package dot

import (
	"cmp"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strings"
	"testing"
	"unicode/utf8"

	"gopkg.in/yaml.v3"
)

const (
	// Average description budget per skill: the discovery envelope scales with the
	// catalog, so adding a skill never buys the others more room, and every
	// description must stay a compact routing cue rather than a summary.
	lifecycleCatalogDescriptionAverageMax = 175
)

var (
	lifecycleTokenPattern = regexp.MustCompile(`[a-z0-9]+`)
	lifecycleStopWords    = map[string]struct{}{
		"a": {}, "an": {}, "and": {}, "any": {}, "are": {}, "as": {}, "at": {}, "be": {}, "before": {},
		"by": {}, "for": {}, "from": {}, "help": {}, "i": {}, "in": {}, "into": {}, "is": {}, "it": {},
		"its": {}, "me": {}, "my": {}, "need": {}, "needs": {}, "of": {}, "on": {}, "or": {}, "our": {},
		"rather": {}, "so": {}, "than": {}, "that": {}, "the": {}, "them": {}, "this": {}, "through": {},
		"to": {}, "use": {}, "using": {}, "want": {}, "we": {}, "when": {}, "where": {}, "with": {},
		"you": {}, "your": {},
	}
)

type lifecycleRoutingBoundaryFile struct {
	Construction  string                     `json:"construction"`
	Created       string                     `json:"created"`
	ProofBoundary string                     `json:"proof_boundary"`
	Purpose       string                     `json:"purpose"`
	Cases         []lifecycleRoutingBoundary `json:"cases"`
	Version       int                        `json:"version"`
}

type lifecycleRoutingBoundary struct {
	Route          *bool    `json:"route"`
	ID             string   `json:"id"`
	Primary        string   `json:"primary"`
	Prompt         string   `json:"prompt"`
	Categories     []string `json:"categories"`
	Expected       []string `json:"expected"`
	Forbidden      []string `json:"forbidden"`
	RequireAllTopK int      `json:"require_all_top_k"`
	TopK           int      `json:"top_k"`
}

func TestLifecycleSkillCatalogDescriptionBudget(t *testing.T) {
	descriptions := readSkillDescriptions(t, skillRepositoryRoot(t))
	total := 0
	seen := make(map[string]string, len(descriptions))
	for name, description := range descriptions {
		total += utf8.RuneCountInString(description)
		normalized := strings.Join(strings.Fields(strings.ToLower(description)), " ")
		if previous, duplicate := seen[normalized]; duplicate {
			t.Errorf("skills %q and %q have identical descriptions", previous, name)
		}
		seen[normalized] = name
	}
	budget := lifecycleCatalogDescriptionAverageMax * len(descriptions)
	if total > budget {
		t.Fatalf("catalog descriptions contain %d characters, exceeding the local %d-character discovery envelope (%d skills x %d); shorten and front-load routing cues", total, budget, len(descriptions), lifecycleCatalogDescriptionAverageMax)
	}
	t.Logf("catalog descriptions contain %d/%d characters", total, budget)
}

func TestLifecycleDescriptionParsesFoldedYAML(t *testing.T) {
	t.Parallel()
	description, err := scanLifecycleDescription(strings.NewReader("---\nname: fixture\ndescription: >-\n  Investigate why tracked code exists\n  before a risky edit.\nlicense: MIT\n---\n\n# Fixture\n"))
	if err != nil {
		t.Fatal(err)
	}
	if want := "Investigate why tracked code exists before a risky edit."; description != want {
		t.Errorf("description = %q, want %q", description, want)
	}
}

func TestLifecycleRoutingCorpusRequiresEveryEvidenceClass(t *testing.T) {
	t.Parallel()
	for _, test := range []struct {
		name          string
		wantErrorPart string
		routed        int
		multi         int
		noRoute       int
	}{
		{name: "complete", routed: 1, multi: 1, noRoute: 1},
		{name: "empty", wantErrorPart: "routable"},
		{name: "no multi intent", routed: 1, noRoute: 1, wantErrorPart: "multi-intent"},
		{name: "no no-route", routed: 1, multi: 1, wantErrorPart: "no-route"},
	} {
		t.Run(test.name, func(t *testing.T) {
			t.Parallel()
			err := lifecycleRoutingCorpusCoverageError(test.routed, test.multi, test.noRoute)
			if test.wantErrorPart == "" {
				if err != nil {
					t.Fatal(err)
				}
				return
			}
			if err == nil || !strings.Contains(err.Error(), test.wantErrorPart) {
				t.Errorf("error = %v, want text %q", err, test.wantErrorPart)
			}
		})
	}
}

func TestLifecycleSkillRoutingBoundaryCorpus(t *testing.T) {
	corpus := readLifecycleRoutingBoundaries(t)
	if corpus.Version != 1 {
		t.Fatalf("routing boundaries: unsupported version %d; replace with 1", corpus.Version)
	}
	if strings.TrimSpace(corpus.Purpose) == "" || strings.TrimSpace(corpus.Construction) == "" || strings.TrimSpace(corpus.ProofBoundary) == "" {
		t.Fatal("routing boundaries: purpose, construction, and proof_boundary must document the corpus provenance and limits")
	}

	descriptions := readSkillDescriptions(t, skillRepositoryRoot(t))
	seenIDs := make(map[string]struct{}, len(corpus.Cases))
	seenPrompts := make(map[string]string, len(corpus.Cases))
	routedCount, multiCount, noRouteCount := 0, 0, 0

	for _, boundary := range corpus.Cases {
		t.Run(boundary.ID, func(t *testing.T) {
			if strings.TrimSpace(boundary.ID) == "" {
				t.Fatal("id is required")
			}
			if _, duplicate := seenIDs[boundary.ID]; duplicate {
				t.Fatalf("duplicate id %q", boundary.ID)
			}
			seenIDs[boundary.ID] = struct{}{}
			checkLifecyclePrompt(t, seenPrompts, boundary.ID, boundary.Prompt)
			if len(boundary.Categories) == 0 {
				t.Error("categories must not be empty")
			}

			shouldRoute := boundary.Route == nil || *boundary.Route
			if !shouldRoute {
				noRouteCount++
				if len(boundary.Expected) != 0 || boundary.Primary != "" || boundary.TopK != 0 || boundary.RequireAllTopK != 0 {
					t.Error("a no-route probe must not declare expected skills, a primary, or rank limits")
				}
				return
			}

			routedCount++
			if len(boundary.Expected) == 0 || !slices.Contains(boundary.Expected, boundary.Primary) {
				t.Fatalf("routable probe must declare a primary inside expected: primary=%q expected=%v", boundary.Primary, boundary.Expected)
			}
			if boundary.TopK < 1 || boundary.TopK > 5 {
				t.Fatalf("top_k %d is outside 1..5", boundary.TopK)
			}
			seenNames := make(map[string]struct{}, len(boundary.Expected)+len(boundary.Forbidden))
			for _, name := range boundary.Expected {
				if _, ok := descriptions[name]; !ok {
					t.Errorf("expected skill %q is absent from the catalog", name)
				}
				if _, duplicate := seenNames[name]; duplicate {
					t.Errorf("expected skill %q is duplicated", name)
				}
				seenNames[name] = struct{}{}
			}
			for _, name := range boundary.Forbidden {
				if _, ok := descriptions[name]; !ok {
					t.Errorf("forbidden skill %q is absent from the catalog", name)
				}
				if _, conflict := seenNames[name]; conflict {
					t.Errorf("skill %q cannot be both expected and forbidden", name)
				}
				seenNames[name] = struct{}{}
			}

			if len(boundary.Expected) > 1 {
				multiCount++
				if boundary.RequireAllTopK < boundary.TopK || boundary.RequireAllTopK > 5 {
					t.Fatalf("require_all_top_k %d must be between top_k %d and 5", boundary.RequireAllTopK, boundary.TopK)
				}
			}
		})
	}
	if err := lifecycleRoutingCorpusCoverageError(routedCount, multiCount, noRouteCount); err != nil {
		t.Fatal(err)
	}
}

func lifecycleRoutingCorpusCoverageError(routedCount, multiCount, noRouteCount int) error {
	if routedCount == 0 {
		return errors.New("routing boundary corpus must contain at least one routable probe")
	}
	if multiCount == 0 {
		return errors.New("routing boundary corpus must contain at least one multi-intent probe")
	}
	if noRouteCount == 0 {
		return errors.New("routing boundary corpus must contain at least one no-route probe")
	}
	return nil
}

func readLifecycleRoutingBoundaries(t *testing.T) lifecycleRoutingBoundaryFile {
	t.Helper()
	path := filepath.Join(skillRepositoryRoot(t), "dot", "testdata", "skills", "routing-boundaries.json")
	file, err := os.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := file.Close(); err != nil {
			t.Errorf("close routing boundaries: %v", err)
		}
	})

	decoder := json.NewDecoder(file)
	decoder.DisallowUnknownFields()
	var corpus lifecycleRoutingBoundaryFile
	if err := decoder.Decode(&corpus); err != nil {
		t.Fatalf("decode routing boundaries: %v", err)
	}
	if err := decoder.Decode(&struct{}{}); err != io.EOF {
		t.Fatalf("decode routing boundaries: expected one JSON value, got %v", err)
	}
	return corpus
}

func checkLifecyclePrompt(t *testing.T, seen map[string]string, owner, prompt string) {
	t.Helper()
	normalized := strings.Join(strings.Fields(strings.ToLower(prompt)), " ")
	if len(normalized) < 20 {
		t.Errorf("%s prompt is too short to describe a realistic routing boundary", owner)
		return
	}
	if previous, duplicate := seen[normalized]; duplicate {
		t.Errorf("%s prompt duplicates %s", owner, previous)
		return
	}
	seen[normalized] = owner
}

func readSkillDescriptions(t *testing.T, repo string) map[string]string {
	t.Helper()
	var files []string
	for _, pattern := range []string{
		filepath.Join(repo, "skills", "*", "SKILL.md"),
		filepath.Join(repo, ".agents", "skills", "*", "SKILL.md"),
	} {
		matched, err := filepath.Glob(pattern)
		if err != nil {
			t.Fatal(err)
		}
		for _, path := range matched {
			// Skip skills that a third-party installer symlinked into the catalog
			// (see isForeignSkillRoot): they are not part of the first-party budget.
			if info, err := os.Lstat(filepath.Dir(path)); err == nil && info.Mode()&os.ModeSymlink != 0 {
				continue
			}
			files = append(files, path)
		}
	}
	descriptions := make(map[string]string, len(files))
	for _, path := range files {
		file, err := os.Open(path)
		if err != nil {
			t.Fatal(err)
		}
		description, scanErr := scanLifecycleDescription(file)
		closeErr := file.Close()
		if scanErr != nil {
			t.Fatalf("%s: %v", path, scanErr)
		}
		if closeErr != nil {
			t.Fatalf("close %s: %v", path, closeErr)
		}
		name := filepath.Base(filepath.Dir(path))
		if strings.TrimSpace(description) == "" {
			t.Fatalf("%s: frontmatter description is empty", path)
		}
		descriptions[name] = description
	}
	return descriptions
}

func scanLifecycleDescription(reader io.Reader) (string, error) {
	data, err := readSkillParsedContent(reader)
	if err != nil {
		return "", err
	}
	normalized := strings.ReplaceAll(string(data), "\r\n", "\n")
	if !strings.HasPrefix(normalized, "---\n") {
		return "", errors.New("frontmatter must start with ---")
	}
	frontmatter := normalized[len("---\n"):]
	before, _, ok := strings.Cut(frontmatter, "\n---\n")
	if !ok {
		return "", errors.New("frontmatter must end with ---")
	}
	var metadata struct {
		Description string `yaml:"description"`
	}
	if err := yaml.Unmarshal([]byte(before), &metadata); err != nil {
		return "", fmt.Errorf("parse frontmatter: %w", err)
	}
	if strings.TrimSpace(metadata.Description) == "" {
		return "", errors.New("frontmatter description is missing")
	}
	return metadata.Description, nil
}

// Lexical overlap is an editing aid, not the routing implementation of any host.
// Keep it transparent: no stemming, invocation parsing, or acceptance threshold.
func TestLifecycleSkillRoutingDiagnostics(t *testing.T) {
	descriptions := readSkillDescriptions(t, skillRepositoryRoot(t))
	matched, total := 0, 0
	for _, probe := range readLifecycleRoutingBoundaries(t).Cases {
		if probe.Route != nil && !*probe.Route {
			continue // Abstention requires a real host; word overlap cannot establish it.
		}
		ranking := rankSkillWords(descriptions, probe.Prompt)
		total++
		if len(ranking) > 0 && ranking[0].Name == probe.Primary && ranking[0].Score > 0 {
			matched++
		}
		t.Logf("%s: expected %s; lexical leaders %v", probe.ID, probe.Primary, ranking[:min(3, len(ranking))])
	}
	t.Logf("lexical rank-1 matches: %d/%d; informational only, not host routing or safety evidence", matched, total)
}

type skillWordRank struct {
	Name  string
	Score float64
}

func rankSkillWords(descriptions map[string]string, prompt string) []skillWordRank {
	query := skillWords(prompt)
	ranking := make([]skillWordRank, 0, len(descriptions))
	for name, description := range descriptions {
		words := skillWords(name + " " + description)
		shared := 0
		for word := range query {
			if _, ok := words[word]; ok {
				shared++
			}
		}
		score := 0.0
		if len(query) > 0 && len(words) > 0 {
			score = float64(shared) / math.Sqrt(float64(len(query)*len(words)))
		}
		ranking = append(ranking, skillWordRank{Name: name, Score: score})
	}
	slices.SortFunc(ranking, func(left, right skillWordRank) int {
		if score := cmp.Compare(right.Score, left.Score); score != 0 {
			return score
		}
		return cmp.Compare(left.Name, right.Name)
	})
	return ranking
}

func skillWords(text string) map[string]struct{} {
	words := make(map[string]struct{})
	for _, word := range lifecycleTokenPattern.FindAllString(strings.ToLower(text), -1) {
		if _, stop := lifecycleStopWords[word]; !stop && len(word) >= 3 {
			words[word] = struct{}{}
		}
	}
	return words
}
