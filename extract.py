"""Parse Word document.xml files into structured JSON for the player pages.

For each paragraph we keep:
  • kind     – 'h2' | 'h3' | 'p' | 'blank' | 'spacer'
  • align    – 'center' | None
  • runs     – list of {'text': str, 'bold': bool, 'italic': bool, 'color': 'red'|None}
The output preserves inline formatting so the renderer can wrap red text in
<span class="rubric">, bold in <strong>, italic in <em>.
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
SRC = Path("extracted")
OUT = Path("content.json")

# Colours treated as the liturgical rubric red. The source documents use
# #980000 almost universally; pure #ff0000 and #cc4125 turn up occasionally.
RUBRIC_HEXES = {"980000", "ff0000", "c00000", "cc0000", "cc4125", "e30000"}

# Typos in the source documents corrected as text is extracted. Add new
# entries here when more misspellings turn up — they're applied per-run
# during run_text, so the fix lives in one place and survives re-extraction.
TYPO_FIXES = {
    "mânturiea": "mântuirea",
    "pe cai mândri": "pe cei mândri",
    "printr-ei": "printr-înșii",
    # Long Vecernia litany of many saints ends with the singular "roagă-te"
    # but should be the plural "rugați-vă". Other singular "roagă-te" usages
    # have "ca să" instead of "să", so the full phrase below is unique.
    "roagă-te lui Hristos Dumnezeu să mântuiască sufletele noastre":
        "rugați-vă lui Hristos Dumnezeu să mântuiască sufletele noastre",
}


def _apply_typo_fixes(text):
    for wrong, right in TYPO_FIXES.items():
        text = text.replace(wrong, right)
    return text


def style_of(p):
    pPr = p.find("w:pPr", NS)
    if pPr is None:
        return None
    pStyle = pPr.find("w:pStyle", NS)
    return pStyle.get(f"{{{NS['w']}}}val") if pStyle is not None else None


def para_bold(p):
    pPr = p.find("w:pPr", NS)
    rPr = pPr.find("w:rPr", NS) if pPr is not None else None
    return rPr is not None and rPr.find("w:b", NS) is not None


def alignment(p):
    pPr = p.find("w:pPr", NS)
    jc = pPr.find("w:jc", NS) if pPr is not None else None
    return jc.get(f"{{{NS['w']}}}val") if jc is not None else None


def run_props(r):
    """Return (bold, italic, color_token) for a run."""
    rPr = r.find("w:rPr", NS)
    if rPr is None:
        return False, False, None
    bold = rPr.find("w:b", NS) is not None
    italic = rPr.find("w:i", NS) is not None
    c = rPr.find("w:color", NS)
    color = None
    if c is not None:
        v = (c.get(f"{{{NS['w']}}}val") or "").lower().lstrip("#")
        if v in RUBRIC_HEXES:
            color = "red"
    return bold, italic, color


def run_text(r):
    parts = []
    for child in r:
        tag = child.tag.split("}")[-1]
        if tag == "t":
            parts.append(child.text or "")
        elif tag == "tab":
            parts.append("\t")
        elif tag == "br":
            parts.append("\n")
    return "".join(parts)


def collect_runs(p):
    """Yield {'text','bold','italic','color'} dicts in document order.
    Coalesces adjacent runs that share formatting so the rendered HTML
    doesn't fragment into one <span> per character."""
    raw = []
    for r in p.findall("w:r", NS):
        b, i, c = run_props(r)
        txt = run_text(r)
        if not txt:
            continue
        raw.append({"text": txt, "bold": b, "italic": i, "color": c})
    merged = []
    for run in raw:
        if merged and all(merged[-1].get(k) == run.get(k) for k in ("bold", "italic", "color")):
            merged[-1]["text"] += run["text"]
        else:
            merged.append(dict(run))
    # Apply typo fixes AFTER merging so corrections can span what used to be
    # separate <w:r> runs in the source docx (e.g. "pe " + "cai" + " mândri").
    for run in merged:
        run["text"] = _apply_typo_fixes(run["text"])
    return merged


def classify(p, runs):
    """Decide paragraph kind from style + run formatting."""
    style = (style_of(p) or "").lower()
    text = "".join(r["text"] for r in runs).strip()
    if not text:
        return "blank"

    if "heading" in style or "title" in style:
        m = re.search(r"(\d+)", style)
        level = int(m.group(1)) if m else 1
        return f"h{min(level, 3)}"

    align = alignment(p)
    all_bold = runs and all(r["bold"] for r in runs)
    all_red  = runs and all(r["color"] == "red" for r in runs)

    # Centered + (all bold or all red) + short → section heading.
    if align == "center" and (all_bold or all_red) and len(text) < 80:
        return "h2"
    # All bold + all red is the rubric heading pattern even without centering.
    if all_bold and all_red and len(text) < 100:
        return "h2"
    if all_bold and len(text) < 100:
        return "h3"
    return "p"


def parse_file(xml_path):
    tree = ET.parse(xml_path)
    body = tree.getroot().find("w:body", NS)
    blocks = []
    for p in body.findall("w:p", NS):
        runs = collect_runs(p)
        kind = classify(p, runs)
        if kind == "blank":
            if blocks and blocks[-1].get("kind") == "spacer":
                continue
            blocks.append({"kind": "spacer"})
            continue
        block = {"kind": kind, "runs": runs}
        a = alignment(p)
        if a:
            block["align"] = a
        blocks.append(block)
    while blocks and blocks[0].get("kind") == "spacer":
        blocks.pop(0)
    while blocks and blocks[-1].get("kind") == "spacer":
        blocks.pop()
    return blocks


def main():
    files = sorted(SRC.glob("*.xml"))
    out = {}
    for f in files:
        out[f.stem] = parse_file(f)
        red_runs = sum(1 for b in out[f.stem] for r in b.get("runs", []) if r.get("color") == "red")
        bold_runs = sum(1 for b in out[f.stem] for r in b.get("runs", []) if r.get("bold"))
        print(f"{f.stem}: {len(out[f.stem])} blocks, {red_runs} red runs, {bold_runs} bold runs")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
