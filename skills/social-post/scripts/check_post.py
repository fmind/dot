"""Check plain-text social copy against channel limits and paste hazards."""

import argparse
import re
import sys
import unicodedata
from pathlib import Path

LIMITS = {"linkedin": 3000, "x": 280, "bluesky": 300}
HASHTAGS = {"linkedin": 3, "x": 2, "bluesky": 3}
URL = re.compile(r"https?://[^\s<>()]+[^\s<>().,;:!?'\"]")
HASHTAG = re.compile(r"(?<![\w&])#\w+")
MARKDOWN = (
    (re.compile(r"\*\*[^*\n]+\*\*"), "Markdown bold"),
    (re.compile(r"^#{1,6} ", re.MULTILINE), "Markdown heading"),
    (re.compile(r"\[[^\]\n]+\]\([^)\s]+\)"), "Markdown link"),
)
# Bracketed slots match in any case; bare markers only in capitals, so "my todo app" stays valid copy.
PLACEHOLDER = re.compile(r"(?i:<[^<>\n]*(?:url|link|handle|date|todo|tbd)[^<>\n]*>)|\b(?:TODO|TBD|XXX)\b")
X_LIGHT = ((0, 4351), (8192, 8205), (8208, 8223), (8242, 8247))  # twitter-text v3 weight-100 ranges


def joins(char: str) -> bool:
    """Return whether a code point extends the preceding visible character."""
    point = ord(char)
    return (
        unicodedata.combining(char) > 0
        or point == 0x200D
        or 0xFE00 <= point <= 0xFE0F
        or 0x1F3FB <= point <= 0x1F3FF
        or 0xE0020 <= point <= 0xE007F
    )


def clusters(text: str) -> list[str]:
    """Approximate user-perceived characters with the standard library."""
    result: list[str] = []
    for char in text:
        previous = result[-1] if result else ""
        flag_pair = 0x1F1E6 <= ord(char) <= 0x1F1FF and len(previous) == 1 and 0x1F1E6 <= ord(previous) <= 0x1F1FF
        if previous and (joins(char) or previous.endswith(chr(0x200D)) or flag_pair):
            result[-1] += char
        else:
            result.append(char)
    return result


def x_weight(text: str) -> int:
    """Weigh text like twitter-text v3: URLs count 23, emoji 2, CJK 2, Latin 1."""
    text = unicodedata.normalize("NFC", text)
    weight = 23 * len(URL.findall(text))
    for cluster in clusters(URL.sub("", text)):
        point = ord(cluster[0])
        light = any(low <= point <= high for low, high in X_LIGHT) and len(cluster) == 1
        weight += 1 if light else 2
    return weight


def length(channel: str, block: str) -> int:
    """Measure one block the way its channel counts characters."""
    if channel == "x":
        return x_weight(block)
    if channel == "bluesky":
        return len(clusters(unicodedata.normalize("NFC", block)))
    return len(block)


def check(channel: str, text: str) -> tuple[list[str], list[str]]:
    """Return errors and warnings for one channel file."""
    errors: list[str] = []
    warnings: list[str] = []
    if not text.strip():
        return ["empty copy"], warnings
    blocks = (
        [text] if channel == "linkedin" else [part.strip("\n") for part in re.split(r"^---$", text, flags=re.MULTILINE)]
    )
    for index, block in enumerate(blocks, 1):
        label = f"block {index}" if len(blocks) > 1 else "post"
        if not block.strip():
            errors.append(f"{label}: empty")
            continue
        size, limit = length(channel, block), LIMITS[channel]
        if size > limit:
            errors.append(f"{label}: {size}/{limit} characters")
        if channel == "bluesky" and len(block.encode()) > 3000:
            errors.append(f"{label}: over 3000 UTF-8 bytes")
    tags = len(HASHTAG.findall(URL.sub("", text)))
    if tags > HASHTAGS[channel]:
        errors.append(f"{tags} hashtags; limit {HASHTAGS[channel]}")
    for pattern, name in MARKDOWN:
        if pattern.search(text):
            errors.append(f"{name} does not render; write plain text")
    if re.search(r"`[^`\n]+`", text):
        warnings.append("backticks show literally; keep them only for commands readers copy")
    if chr(0x2014) in text:  # em-dash
        errors.append("em-dash found; use a period, comma, or colon")
    if PLACEHOLDER.search(text):
        errors.append("placeholder found; name the missing value instead")
    if any("fmind.dev" in url and "utm_source=" not in url and "/articles/" in url for url in URL.findall(text)):
        warnings.append("fmind.dev article link without utm_source")
    if channel == "linkedin":
        first = text.strip().splitlines()[0]
        if len(first) > 200:
            warnings.append(f"first line {len(first)} characters; the feed folds near 200")
        if re.search(r"(?:link|url)\s+in\s+(?:the\s+)?(?:first\s+)?comment", text, re.IGNORECASE):
            errors.append("link-in-comment phrasing; put at most one link in the body")
        if re.search(r"[^\n]\n\n[^\n]", text):
            warnings.append("paragraphs separated by one empty line; LinkedIn paste may collapse them, use two")
    return errors, warnings


def main() -> int:
    """Check a file or stdin and exit nonzero when any error is found."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", required=True, choices=sorted(LIMITS))
    parser.add_argument("source", nargs="?", default="-", help="UTF-8 file, or - for stdin")
    args = parser.parse_args()
    try:
        data = sys.stdin.buffer.read() if args.source == "-" else Path(args.source).read_bytes()
        text = data.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        sys.stderr.write(f"Cannot read {args.source}: {error}\n")
        return 2
    errors, warnings = check(args.channel, text.replace("\r\n", "\n"))
    for message in errors:
        sys.stdout.write(f"ERROR {args.channel}: {message}\n")
    for message in warnings:
        sys.stdout.write(f"WARN {args.channel}: {message}\n")
    if not errors:
        sys.stdout.write(f"OK {args.channel}: {len(warnings)} warning(s)\n")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
