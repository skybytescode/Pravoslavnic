"""Split Repository/Ceasurile.docx into one extracted/<slug>.xml per service.

The source is a single Word document holding all twelve services back to
back, each opened by a short heading paragraph ("Ceasul 1", "Mijloceasul
Intai", "VECERNIA (ora 18:00)", …). We locate those headings, slice the body
between them and write each slice as a standalone document.xml that
extract.py can parse exactly like the per-file sources of Ceaslovnic. The
heading paragraph itself is dropped — the page title comes from the schedule.
"""
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
SRC = ROOT / "Repository" / "Ceasurile.docx"
OUT = ROOT / "extracted"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"

# (slug, pattern matched against the whole normalised heading paragraph).
# Normalisation: lower-case, diacritics stripped, whitespace collapsed.
SECTIONS = [
    ("03-ceasul-1",      r"ceasul 1"),
    ("04-mijloceasul-1", r"mijloceasul intai"),
    ("05-ceasul-3",      r"ceasul al treilea"),
    ("06-mijloceasul-3", r"mijloceasul al treilea"),
    ("07-ceasul-6",      r"ceasul al saselea"),
    ("08-mijloceasul-6", r"mijloceasul al saselea"),
    ("09-ceasul-9",      r"ceasul al noualea"),
    ("10-mijloceasul-9", r"mijloceasul al no(u)?ualea|mijloceasul al noulea"),
    ("11-vecernia",      r"vecernia( \(ora 18:00\))?"),
    ("12-pavecernita",   r"pavecernita mica ?(\(21:00\))?"),
    ("01-miezonoptica",  r"miezonoptica"),
    ("02-utrenia",       r"utrenia"),
]


def normalise(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip().lower()


def para_text(p):
    return "".join(t.text or "" for t in p.iter(f"{W}t"))


def main():
    ET.register_namespace("w", W_NS)
    with zipfile.ZipFile(SRC) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(f"{W}body")
    paras = body.findall(f"{W}p")

    starts = []
    for slug, pattern in SECTIONS:
        hits = [i for i, p in enumerate(paras) if re.fullmatch(pattern, normalise(para_text(p)))]
        if len(hits) != 1:
            raise SystemExit(f"{slug}: expected exactly one heading matching {pattern!r}, found {hits}")
        starts.append((hits[0], slug))
    starts.sort()
    if starts[0][0] != 0:
        print(f"note: {starts[0][0]} paragraph(s) before the first heading are ignored")

    OUT.mkdir(exist_ok=True)
    for n, (start, slug) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(paras)
        doc = ET.Element(f"{W}document")
        part = ET.SubElement(doc, f"{W}body")
        part.extend(paras[start + 1 : end])
        (OUT / f"{slug}.xml").write_bytes(ET.tostring(doc, encoding="utf-8", xml_declaration=True))
        print(f"{slug}: paragraphs {start + 1}–{end - 1}")


if __name__ == "__main__":
    main()
