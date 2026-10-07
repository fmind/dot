---
name: social-post
description: "Write paste-safe LinkedIn, X, and Bluesky posts within channel limits."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/social-post
  created: "2026-10-04"
  updated: "2026-10-07"
---

# Social Post

Adapt a source (article, release, announcement, talk) into native copy for LinkedIn, X, or Bluesky that survives copy-paste into each composer. Posting is always manual: never post, schedule, or automate a channel. When the repository has its own post workflow (for example `write-posts` in a publishing project), follow it; [technical-publishing](../technical-publishing/SKILL.md) owns article and announcement packages, channel selection, canonical publication, and the publication log; this skill writes and checks the copy.

## Workflow

1. **Read the source and the voice**: the full source, the author's notes, and the project's identity or voice file when present. Extract the thesis, one concrete detail or result, its boundary, and the single best link. Never add a personal story, metric, or client the source does not carry.
1. **Write each channel natively**, one file or block per channel, never the same opening twice:
   - **LinkedIn**: a self-contained note worth reading without clicking. The first line carries the tension or sharpest finding and stays under about 200 characters (the feed fold). Up to 3000 characters, at most 3 precise hashtags. An article adaptation carries no link (it must stand alone); an announcement or episode at most one, in the body (never "link in first comment"). Separate paragraphs with two empty lines: LinkedIn paste can collapse single ones.
   - **X**: one post or a real thread; split blocks with a line containing only `---`, each useful alone and at most 280 weighted characters (URLs count 23, emoji and CJK count 2). At most 2 hashtags.
   - **Bluesky**: a conversational note, not a trimmed X post; at most 300 characters per block and 3 hashtags.
1. **Write plain text**: no Markdown bold, headings, or `[text](url)` links, since none render; write bare URLs and `-` or numbered lines for lists. Avoid Unicode "bold" letters: screen readers and search treat them as symbols. No em-dashes; use periods, commas, or colons. Tag `fmind.dev` article links with `?utm_source=<channel>`.
1. **Check each channel** with the bundled [checker](scripts/check_post.py); fix every `ERROR`, judge each `WARN`. Its X and Bluesky counts approximate grapheme rules with the standard library; a project checker such as `pub check`, when present, is authoritative.

   ```bash
   python -I ~/.agents/skills/social-post/scripts/check_post.py --channel linkedin posts/linkedin.txt
   python -I ~/.agents/skills/social-post/scripts/check_post.py --channel x - <<'POST'
   Draft goes here.
   POST
   ```

1. **Hand off**: show each post in a plain-text block, name any missing URL instead of inventing one, and offer [clipboard](../clipboard/SKILL.md) to copy the chosen channel.

## Gotchas

- **Cut generated-sounding slop**: hype openers, "Here's why 🧵", engagement bait, a bold lead on every line, and a summary closing every paragraph read as generated. One strong claim and one real detail beat a list of features.
- **Rendered chat collapses whitespace**: copy from the file or clipboard, not from rendered Markdown, to keep LinkedIn's double empty lines.
- **Platform rules drift**: recheck the current limits before relying on them: [LinkedIn](https://www.linkedin.com/help/linkedin/answer/a528176), [X counting](https://docs.x.com/resources/fundamentals/counting-characters), [Bluesky posts](https://docs.bsky.app/docs/advanced-guides/posts).

## Documentation

- Companion skills: [technical-publishing](../technical-publishing/SKILL.md) (packages and canonical publication), [fact-check](../fact-check/SKILL.md) (claims and links before posting), [clipboard](../clipboard/SKILL.md) (copy the result).
