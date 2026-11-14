#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["python-pptx==1.0.2"]
# ///
"""Generate an editable-shape 16:9 PowerPoint deck styled with the Fmind Theme for Google Slides import."""

from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Inches, Pt

# Fmind DESIGN.md palette tokens.
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PANEL = RGBColor(0xF1, 0xF3, 0xF4)
BORDER = RGBColor(0x9A, 0xA0, 0xA6)
MUTED = RGBColor(0x59, 0x5D, 0x62)
FOREGROUND = RGBColor(0x20, 0x21, 0x24)
PRIMARY = RGBColor(0x17, 0x4E, 0xA6)
SELECTION = RGBColor(0xD2, 0xE3, 0xFC)
SUCCESS = RGBColor(0x0D, 0x65, 0x2D)
SANS_FONT = "Google Sans"


@dataclass(frozen=True, slots=True)
class SlideCard:
    title: str
    body: str
    accent: RGBColor = PRIMARY
    fill: RGBColor = PANEL


def _new_presentation() -> Presentation:
    prs = Presentation()
    prs.slide_width = Inches(10.0)
    prs.slide_height = Inches(5.625)
    return prs


def _png_dimensions(png_path: Path) -> tuple[int, int]:
    """Read pixel (width, height) from a PNG IHDR chunk using stdlib struct."""
    header = png_path.read_bytes()[:24]
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        msg = f"Expected a valid PNG image for --figure: {png_path}"
        raise ValueError(msg)
    width, height = struct.unpack(">II", header[16:24])
    if width <= 0 or height <= 0:
        msg = f"Invalid PNG dimensions in {png_path}: {width}x{height}"
        raise ValueError(msg)
    return int(width), int(height)


def _add_note(slide: Any, text: str) -> None:
    if text:
        slide.notes_slide.notes_text_frame.text = text


def _style_run(run: Any, *, text: str, size: int, color: RGBColor, bold: bool = False) -> None:
    run.text = text
    run.font.name = SANS_FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def _add_textbox(
    slide: Any,
    *,
    left: float,
    top: float,
    width: float,
    height: float,
    text: str,
    size: int,
    color: RGBColor = FOREGROUND,
    bold: bool = False,
) -> None:
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.TOP
    _style_run(frame.paragraphs[0].add_run(), text=text, size=size, color=color, bold=bold)


def _add_header(slide: Any, *, kicker: str, title: str, takeaway: str) -> None:
    _add_textbox(slide, left=0.55, top=0.32, width=8.9, height=0.28, text=kicker, size=12, color=PRIMARY, bold=True)
    _add_textbox(slide, left=0.55, top=0.58, width=8.9, height=0.58, text=title, size=26, color=PRIMARY, bold=True)
    _add_textbox(slide, left=0.55, top=1.18, width=8.9, height=0.34, text=takeaway, size=15, color=MUTED)
    rule = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.55), Inches(1.56), Inches(8.9), Inches(0.015))
    rule.fill.solid()
    rule.fill.fore_color.rgb = BORDER
    rule.line.fill.background()


def _add_card(slide: Any, card: SlideCard, *, left: float, top: float, width: float, height: float) -> None:
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    shape.adjustments[0] = 0.06
    shape.fill.solid()
    shape.fill.fore_color.rgb = card.fill
    shape.line.color.rgb = BORDER if card.fill == PANEL else card.accent
    shape.line.width = Pt(1.25)
    frame = shape.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.TOP
    frame.margin_left = Inches(0.22)
    frame.margin_right = Inches(0.22)
    frame.margin_top = Inches(0.20)
    frame.margin_bottom = Inches(0.18)
    _style_run(frame.paragraphs[0].add_run(), text=card.title, size=17, color=card.accent, bold=True)
    for line in card.body.splitlines():
        para = frame.add_paragraph()
        para.space_before = Pt(8)
        _style_run(para.add_run(), text=line, size=15, color=FOREGROUND)


def _add_callout(slide: Any, title: str, body: str, *, top: float = 4.50) -> None:
    banner = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.55), Inches(top), Inches(8.9), Inches(0.72))
    banner.fill.solid()
    banner.fill.fore_color.rgb = SELECTION
    banner.line.fill.background()
    frame = banner.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    frame.margin_left = Inches(0.26)
    frame.margin_right = Inches(0.22)
    para = frame.paragraphs[0]
    _style_run(para.add_run(), text=f"{title} ", size=15, color=PRIMARY, bold=True)
    _style_run(para.add_run(), text=body, size=15, color=FOREGROUND)
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.55), Inches(top), Inches(0.06), Inches(0.72))
    bar.fill.solid()
    bar.fill.fore_color.rgb = PRIMARY
    bar.line.fill.background()


def build_deck(output_path: Path, *, title: str, figure_path: Path | None = None) -> Path:
    """Build a 3-slide editable-shape presentation ready for private Google Slides import."""
    prs = _new_presentation()
    prs.core_properties.title = title
    blank = prs.slide_layouts[6]

    # Slide 1: Cover
    cover = prs.slides.add_slide(blank)
    accent = cover.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.65), Inches(1.45), Inches(0.08), Inches(2.3))
    accent.fill.solid()
    accent.fill.fore_color.rgb = PRIMARY
    accent.line.fill.background()
    _add_textbox(cover, left=0.92, top=1.42, width=8.2, height=1.25, text=title, size=36, color=PRIMARY, bold=True)
    _add_textbox(
        cover,
        left=0.92,
        top=2.72,
        width=8.2,
        height=0.85,
        text="Same reliability SLA at 38% lower monthly spend.",
        size=18,
        color=FOREGROUND,
    )
    _add_textbox(
        cover,
        left=0.92,
        top=4.68,
        width=8.2,
        height=0.38,
        text="Infrastructure decision brief · Nov 14, 2026",
        size=13,
        color=MUTED,
    )
    _add_note(cover, "Open with the decision ask: approve Provider B before Friday 17:00 CET.")

    # Slide 2: Executive KPI cards
    summary = prs.slides.add_slide(blank)
    _add_header(
        summary,
        kicker="Decision signal",
        title="Provider B cuts annual spend by $42k",
        takeaway="Steady capacity verified over 14-day shadow replay.",
    )
    cards = (
        SlideCard("Annual spend", "-38%\n$68k vs $110k baseline", accent=SUCCESS, fill=WHITE),
        SlideCard("Shadow SLA", "99.9%\nZero failover drops", accent=PRIMARY),
        SlideCard("Cutover", "2 weeks\nZero planned downtime", accent=PRIMARY, fill=SELECTION),
    )
    for idx, card in enumerate(cards):
        _add_card(summary, card, left=0.55 + idx * 3.04, top=1.80, width=2.82, height=2.38)
    _add_callout(summary, "Decision ask:", "Approve Provider B terms before Friday 17:00 CET.")
    _add_note(summary, "Put full cost tables and assumptions in speaker notes rather than on-slide.")

    # Slide 3: Side-by-side comparison (embeds optional Typst PNG figure clamped inside bounds)
    compare = prs.slides.add_slide(blank)
    _add_header(
        compare,
        kicker="Comparison",
        title="Lower spend without adding latency risk",
        takeaway="Colocated storage trims tail latency in half.",
    )
    _add_card(
        compare,
        SlideCard(
            "Recommendation",
            "Shift 50% traffic in Week 1 with automated rollback.",
            accent=PRIMARY,
            fill=SELECTION,
        ),
        left=0.55,
        top=1.80,
        width=4.25,
        height=3.25,
    )
    if figure_path is not None:
        w_px, h_px = _png_dimensions(figure_path)
        max_w, max_h = 4.4, 3.25
        scale = min(max_w / w_px, max_h / h_px)
        pic_w = Inches(w_px * scale)
        pic_h = Inches(h_px * scale)
        pic_left = Inches(5.05 + (max_w - w_px * scale) / 2.0)
        pic_top = Inches(1.80 + (max_h - h_px * scale) / 2.0)
        compare.shapes.add_picture(str(figure_path), pic_left, pic_top, width=pic_w, height=pic_h)
    else:
        _add_card(
            compare,
            SlideCard(
                "Typst visual",
                "Run build_typst_deck.py render figure-card.typ and pass --figure figure-card.png.",
                accent=MUTED,
            ),
            left=5.05,
            top=1.80,
            width=4.4,
            height=3.25,
        )
    _add_note(compare, "Upload via build_typst_deck.py upload editable-deck.pptx --google-slides --source-dir .")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False, suggest_on_error=True)
    parser.add_argument("-o", "--output", type=Path, default=Path("editable-deck.pptx"), help="Output .pptx path.")
    parser.add_argument("--title", default="Architecture Decision Briefing", help="Deck cover title.")
    parser.add_argument("--figure", type=Path, default=None, help="Optional 2x PNG figure rendered by Typst.")
    args = parser.parse_args(argv)
    if args.figure is not None and not args.figure.is_file():
        sys.stderr.write(f"Error: Missing figure file: {args.figure}\n")
        return 1
    out = build_deck(
        args.output.resolve(), title=args.title, figure_path=args.figure.resolve() if args.figure else None
    )
    sys.stdout.write(f"{out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
