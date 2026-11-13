#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["python-pptx==1.0.2"]
# ///
"""Generate an editable-shape 16:9 PowerPoint deck styled with the Fmind Theme for Google Slides import."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

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


def _add_note(slide: object, text: str) -> None:
    if text:
        slide.notes_slide.notes_text_frame.text = text  # type: ignore[attr-defined]


def _add_textbox(
    slide: object,
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
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))  # type: ignore[attr-defined]
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.TOP
    paragraph = frame.paragraphs[0]
    run = paragraph.add_run()
    run.text = text
    run.font.name = SANS_FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def _add_header(slide: object, *, kicker: str, title: str, takeaway: str) -> None:
    _add_textbox(
        slide, left=0.55, top=0.35, width=8.9, height=0.25, text=kicker.upper(), size=10, color=PRIMARY, bold=True
    )
    _add_textbox(slide, left=0.55, top=0.60, width=8.9, height=0.55, text=title, size=22, color=PRIMARY, bold=True)
    _add_textbox(slide, left=0.55, top=1.15, width=8.9, height=0.32, text=takeaway, size=13, color=MUTED)
    rule = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.55), Inches(1.52), Inches(8.9), Inches(0.015))  # type: ignore[attr-defined]
    rule.fill.solid()
    rule.fill.fore_color.rgb = BORDER
    rule.line.fill.background()


def _add_card(slide: object, card: SlideCard, *, left: float, top: float, width: float, height: float) -> None:
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )  # type: ignore[attr-defined]
    shape.adjustments[0] = 0.06
    shape.fill.solid()
    shape.fill.fore_color.rgb = card.fill
    shape.line.color.rgb = BORDER if card.fill == PANEL else card.accent
    shape.line.width = Pt(1.25)
    _add_textbox(
        slide,
        left=left + 0.22,
        top=top + 0.20,
        width=width - 0.44,
        height=0.38,
        text=card.title,
        size=16,
        color=card.accent,
        bold=True,
    )
    _add_textbox(
        slide,
        left=left + 0.22,
        top=top + 0.65,
        width=width - 0.44,
        height=height - 0.85,
        text=card.body,
        size=13,
        color=FOREGROUND,
    )


def _add_callout(slide: object, title: str, body: str, *, top: float = 4.55) -> None:
    banner = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.55), Inches(top), Inches(8.9), Inches(0.68))  # type: ignore[attr-defined]
    banner.fill.solid()
    banner.fill.fore_color.rgb = SELECTION
    banner.line.fill.background()
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.55), Inches(top), Inches(0.06), Inches(0.68))  # type: ignore[attr-defined]
    bar.fill.solid()
    bar.fill.fore_color.rgb = PRIMARY
    bar.line.fill.background()
    _add_textbox(
        slide,
        left=0.75,
        top=top + 0.10,
        width=8.5,
        height=0.50,
        text=f"{title} {body}",
        size=13,
        color=FOREGROUND,
        bold=True,
    )


def build_deck(output_path: Path, *, title: str, figure_path: Path | None = None) -> Path:
    """Build a 3-slide editable-shape presentation ready for private Google Slides import."""
    prs = _new_presentation()
    blank = prs.slide_layouts[6]

    # Slide 1: Cover
    cover = prs.slides.add_slide(blank)
    accent = cover.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.65), Inches(1.45), Inches(0.08), Inches(2.2))
    accent.fill.solid()
    accent.fill.fore_color.rgb = PRIMARY
    accent.line.fill.background()
    _add_textbox(cover, left=0.92, top=1.45, width=8.2, height=1.2, text=title, size=34, color=PRIMARY, bold=True)
    _add_textbox(
        cover,
        left=0.92,
        top=2.65,
        width=8.2,
        height=0.9,
        text="Editable Google Slides layout paired with Retina Typst visuals.",
        size=16,
        color=FOREGROUND,
    )
    _add_addendum = "Edit cards directly in Google Slides; keep source figures synced in Drive assets/."
    _add_textbox(cover, left=0.92, top=4.75, width=8.2, height=0.35, text=_add_addendum, size=11, color=MUTED)
    _add_note(cover, "Open with the single decision ask in 20 seconds; leave supporting metrics for slide 2.")

    # Slide 2: Executive KPI cards
    summary = prs.slides.add_slide(blank)
    _add_header(
        summary,
        kicker="Executive signal",
        title="Editable summary cards with Fmind contrast",
        takeaway="One highlighted ask backed by three crisp metrics.",
    )
    cards = (
        SlideCard("Cost impact", "-40% monthly spend\nSteady committed capacity", accent=PRIMARY),
        SlideCard("Reliability", "99.2% SLA pass\nZero unscheduled failover", accent=SUCCESS, fill=WHITE),
        SlideCard("Delivery window", "3-week rollout\nStaged shadow verification", accent=PRIMARY, fill=SELECTION),
    )
    for idx, card in enumerate(cards):
        _add_card(summary, card, left=0.55 + idx * 3.04, top=1.78, width=2.82, height=2.45)
    _add_callout(summary, "Decision ask:", "Approve Week-1 baseline and revisit committed capacity on Day 21.")
    _add_note(summary, "Keep detailed cost methodology and raw benchmarks off-slide in speaker notes.")

    # Slide 3: Side-by-side comparison (embeds optional Typst PNG figure on the right)
    compare = prs.slides.add_slide(blank)
    _add_header(
        compare,
        kicker="Options compared",
        title="Native editable text beside branded Typst figures",
        takeaway="Update slide copy in Google Slides while preserving crisp vector-grade charts.",
    )
    _add_card(
        compare,
        SlideCard(
            "Key trade-offs",
            "Keep prose concise: 1-3 signals per card, high contrast, open whitespace.",
            accent=PRIMARY,
            fill=SELECTION,
        ),
        left=0.55,
        top=1.78,
        width=4.25,
        height=3.30,
    )
    if figure_path is not None:
        compare.shapes.add_picture(str(figure_path), Inches(5.05), Inches(1.78), width=Inches(4.4))
    else:
        _add_card(
            compare,
            SlideCard(
                "Typst chart placeholder",
                "Pass --figure figures/chart.png to embed a 2x Retina Typst diagram here.",
                accent=MUTED,
            ),
            left=5.05,
            top=1.78,
            width=4.4,
            height=3.30,
        )
    _add_note(compare, "Upload with build_typst_deck.py upload <deck.pptx> --google-slides --source-dir .")

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
