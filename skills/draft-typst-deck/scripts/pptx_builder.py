"""Stdlib OOXML 16:9 .pptx builder and archive validator for rendered slide PNGs and notes."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
from xml.sax.saxutils import unescape as xml_unescape

SLIDE_CX = 9144000  # 10 in at 914400 EMU/in (16:9 widescreen)
SLIDE_CY = 5143500  # 5.625 in

_NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
_NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_NS_OD_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _rels_xml(entries: list[tuple[str, str, str]]) -> bytes:
    items = "".join(
        f'<Relationship Id="{xml_escape(rid)}" Type="{xml_escape(rtype)}" Target="{xml_escape(target)}"/>'
        for rid, rtype, target in entries
    )
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{_NS_REL}">{items}</Relationships>'
    ).encode()


def _notes_slide_xml(note_text: str) -> bytes:
    paragraphs = note_text.splitlines() if note_text else []
    if not paragraphs:
        p_xml = '<a:p><a:endParaRPr lang="en-US"/></a:p>'
    else:
        p_xml = "".join(
            f'<a:p><a:r><a:rPr lang="en-US"/><a:t>{xml_escape(line)}</a:t></a:r></a:p>'
            if line
            else '<a:p><a:endParaRPr lang="en-US"/></a:p>'
            for line in paragraphs
        )
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:notes xmlns:a="{_NS_A}" xmlns:r="{_NS_OD_REL}" xmlns:p="{_NS_P}">'
        "<p:cSld><p:spTree>"
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Slide Image"/><p:cNvSpPr><a:spLocks noGrp="1" noRot="1" noChangeAspect="1"/></p:cNvSpPr><p:nvPr><p:ph type="sldImg"/></p:nvPr></p:nvSpPr><p:spPr/></p:sp>'
        '<p:sp><p:nvSpPr><p:cNvPr id="3" name="Notes"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr>'
        f"<p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>{p_xml}</p:txBody></p:sp>"
        "</p:spTree></p:cSld></p:notes>"
    ).encode()


def _slide_xml(index: int) -> bytes:
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sld xmlns:a="{_NS_A}" xmlns:r="{_NS_OD_REL}" xmlns:p="{_NS_P}">'
        "<p:cSld><p:spTree>"
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        f'<p:pic><p:nvPicPr><p:cNvPr id="2" name="Slide {index}"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
        '<p:blipFill><a:blip r:embed="rId2" cstate="print"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
        f'<p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{SLIDE_CX}" cy="{SLIDE_CY}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
        "</p:spTree></p:cSld></p:sld>"
    ).encode()


def build_pptx(
    slide_pngs: list[Path],
    output_pptx: Path,
    *,
    title: str,
    speaker_notes: dict[int, str] | None = None,
) -> Path:
    """Pack rendered 16:9 PNG slides and optional per-slide speaker notes into a stdlib OOXML .pptx."""
    if not slide_pngs:
        raise ValueError("Cannot build .pptx with zero slide PNGs.")
    notes = speaker_notes or {}
    output_pptx.parent.mkdir(parents=True, exist_ok=True)
    n = len(slide_pngs)

    content_overrides = [
        ("/ppt/presentation.xml", "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"),
        (
            "/ppt/slideMasters/slideMaster1.xml",
            "application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml",
        ),
        (
            "/ppt/slideLayouts/slideLayout1.xml",
            "application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml",
        ),
        (
            "/ppt/notesMasters/notesMaster1.xml",
            "application/vnd.openxmlformats-officedocument.presentationml.notesMaster+xml",
        ),
        ("/ppt/theme/theme1.xml", "application/vnd.openxmlformats-officedocument.theme+xml"),
        ("/docProps/core.xml", "application/vnd.openxmlformats-package.core-properties+xml"),
    ]
    for idx in range(1, n + 1):
        content_overrides.append(
            (f"/ppt/slides/slide{idx}.xml", "application/vnd.openxmlformats-officedocument.presentationml.slide+xml")
        )
        content_overrides.append(
            (
                f"/ppt/notesSlides/notesSlide{idx}.xml",
                "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml",
            )
        )
    content_types = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="{_NS_CT}">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="png" ContentType="image/png"/>'
        + "".join(f'<Override PartName="{p}" ContentType="{ct}"/>' for p, ct in content_overrides)
        + "</Types>"
    ).encode("utf-8")

    pres_rels = [("rId1", f"{_NS_OD_REL}/slideMaster", "slideMasters/slideMaster1.xml")]
    sld_ids = []
    for idx in range(1, n + 1):
        rid = f"rId{idx + 1}"
        pres_rels.append((rid, f"{_NS_OD_REL}/slide", f"slides/slide{idx}.xml"))
        sld_ids.append(f'<p:sldId id="{255 + idx}" r:id="{rid}"/>')
    notes_master_rid = f"rId{n + 2}"
    theme_rid = f"rId{n + 3}"
    pres_rels.append((notes_master_rid, f"{_NS_OD_REL}/notesMaster", "notesMasters/notesMaster1.xml"))
    pres_rels.append((theme_rid, f"{_NS_OD_REL}/theme", "theme/theme1.xml"))

    presentation_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:presentation xmlns:a="{_NS_A}" xmlns:r="{_NS_OD_REL}" xmlns:p="{_NS_P}">'
        '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
        f'<p:notesMasterIdLst><p:notesMasterId r:id="{notes_master_rid}"/></p:notesMasterIdLst>'
        f"<p:sldIdLst>{''.join(sld_ids)}</p:sldIdLst>"
        f'<p:sldSz cx="{SLIDE_CX}" cy="{SLIDE_CY}" type="screen16x9"/><p:notesSz cx="6858000" cy="9144000"/>'
        "</p:presentation>"
    ).encode()

    theme_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:theme xmlns:a="{_NS_A}" name="Fmind">'
        '<a:themeElements><a:clrScheme name="Fmind">'
        '<a:dk1><a:srgbClr val="202124"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>'
        '<a:dk2><a:srgbClr val="595D62"/></a:dk2><a:lt2><a:srgbClr val="F1F3F4"/></a:lt2>'
        '<a:accent1><a:srgbClr val="174EA6"/></a:accent1><a:accent2><a:srgbClr val="00636D"/></a:accent2>'
        '<a:accent3><a:srgbClr val="934900"/></a:accent3><a:accent4><a:srgbClr val="0D652D"/></a:accent4>'
        '<a:accent5><a:srgbClr val="681DA8"/></a:accent5><a:accent6><a:srgbClr val="A50E0E"/></a:accent6>'
        '<a:hlink><a:srgbClr val="174EA6"/></a:hlink><a:folHlink><a:srgbClr val="681DA8"/></a:folHlink>'
        '</a:clrScheme><a:fontScheme name="Fmind"><a:majorFont><a:latin typeface="Google Sans"/>'
        '<a:ea typeface=""/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Google Sans"/>'
        '<a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme>'
        '<a:fmtScheme name="Fmind"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>'
        '<a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst>'
        "<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>"
        '<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>'
        "</a:fmtScheme></a:themeElements></a:theme>"
    ).encode()

    slide_master_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sldMaster xmlns:a="{_NS_A}" xmlns:r="{_NS_OD_REL}" xmlns:p="{_NS_P}">'
        '<p:cSld><p:bg><p:bgRef idx="1001"><a:schemeClr val="bg1"/></p:bgRef></p:bg><p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        "</p:spTree></p:cSld>"
        '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" '
        'accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
        '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
        "</p:sldMaster>"
    ).encode()

    slide_layout_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sldLayout xmlns:a="{_NS_A}" xmlns:r="{_NS_OD_REL}" xmlns:p="{_NS_P}" type="blank" preserve="1">'
        '<p:cSld name="Blank"><p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        "</p:spTree></p:cSld></p:sldLayout>"
    ).encode()

    notes_master_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:notesMaster xmlns:a="{_NS_A}" xmlns:r="{_NS_OD_REL}" xmlns:p="{_NS_P}">'
        "<p:cSld><p:spTree>"
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        "</p:spTree></p:cSld>"
        '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" '
        'accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
        "</p:notesMaster>"
    ).encode()

    core_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f"<dc:title>{xml_escape(title)}</dc:title></cp:coreProperties>"
    ).encode()

    with zipfile.ZipFile(output_pptx, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr(
            "_rels/.rels",
            _rels_xml(
                [
                    ("rId1", f"{_NS_OD_REL}/officeDocument", "ppt/presentation.xml"),
                    (
                        "rId2",
                        "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties",
                        "docProps/core.xml",
                    ),
                ]
            ),
        )
        zf.writestr("docProps/core.xml", core_xml)
        zf.writestr("ppt/presentation.xml", presentation_xml)
        zf.writestr("ppt/_rels/presentation.xml.rels", _rels_xml(pres_rels))
        zf.writestr("ppt/theme/theme1.xml", theme_xml)
        zf.writestr("ppt/slideMasters/slideMaster1.xml", slide_master_xml)
        zf.writestr(
            "ppt/slideMasters/_rels/slideMaster1.xml.rels",
            _rels_xml(
                [
                    ("rId1", f"{_NS_OD_REL}/slideLayout", "../slideLayouts/slideLayout1.xml"),
                    ("rId2", f"{_NS_OD_REL}/theme", "../theme/theme1.xml"),
                ]
            ),
        )
        zf.writestr("ppt/slideLayouts/slideLayout1.xml", slide_layout_xml)
        zf.writestr(
            "ppt/slideLayouts/_rels/slideLayout1.xml.rels",
            _rels_xml([("rId1", f"{_NS_OD_REL}/slideMaster", "../slideMasters/slideMaster1.xml")]),
        )
        zf.writestr("ppt/notesMasters/notesMaster1.xml", notes_master_xml)
        zf.writestr(
            "ppt/notesMasters/_rels/notesMaster1.xml.rels",
            _rels_xml([("rId1", f"{_NS_OD_REL}/theme", "../theme/theme1.xml")]),
        )
        for idx, png_path in enumerate(slide_pngs, start=1):
            media_name = f"slide-{idx:02d}.png"
            zf.writestr(f"ppt/media/{media_name}", png_path.read_bytes(), compress_type=zipfile.ZIP_STORED)
            zf.writestr(f"ppt/slides/slide{idx}.xml", _slide_xml(idx))
            zf.writestr(
                f"ppt/slides/_rels/slide{idx}.xml.rels",
                _rels_xml(
                    [
                        ("rId1", f"{_NS_OD_REL}/slideLayout", "../slideLayouts/slideLayout1.xml"),
                        ("rId2", f"{_NS_OD_REL}/image", f"../media/{media_name}"),
                        ("rId3", f"{_NS_OD_REL}/notesSlide", f"../notesSlides/notesSlide{idx}.xml"),
                    ]
                ),
            )
            zf.writestr(f"ppt/notesSlides/notesSlide{idx}.xml", _notes_slide_xml(notes.get(idx, "")))
            zf.writestr(
                f"ppt/notesSlides/_rels/notesSlide{idx}.xml.rels",
                _rels_xml(
                    [
                        ("rId1", f"{_NS_OD_REL}/slide", f"../slides/slide{idx}.xml"),
                        ("rId2", f"{_NS_OD_REL}/notesMaster", "../notesMasters/notesMaster1.xml"),
                    ]
                ),
            )
    return output_pptx


def inspect_pptx_metadata(pptx_path: Path) -> tuple[int, str | None]:
    """Validate an OOXML .pptx archive and return `(slide_count, core_title)`."""
    try:
        with zipfile.ZipFile(pptx_path, "r") as zf:
            names = set(zf.namelist())
            core_xml = (
                zf.read("docProps/core.xml").decode("utf-8", errors="replace") if "docProps/core.xml" in names else ""
            )
    except zipfile.BadZipFile as exc:
        raise ValueError(f"File is not a valid .pptx OOXML archive: {pptx_path}") from exc
    if "ppt/presentation.xml" not in names:
        raise ValueError(f"Archive is missing ppt/presentation.xml: {pptx_path}")
    slides = [name for name in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)]
    if not slides:
        raise ValueError(f".pptx contains zero slides: {pptx_path}")
    title: str | None = None
    if core_xml and (
        match := re.search(r"<(?:[A-Za-z0-9_-]+:)?title[^>]*>(.*?)</(?:[A-Za-z0-9_-]+:)?title>", core_xml, re.DOTALL)
    ):
        parsed = xml_unescape(match.group(1)).strip()
        if parsed:
            title = parsed
    return len(slides), title
