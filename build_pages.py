"""Generate docs/content/*.html from content.json + the schedule.

Renders the parsed Word content with Orthodox-book typography:
  • rubric (red) runs are wrapped in <span class="rubric">
  • bold runs become <strong>, italic <em>
  • a red drop-cap opens the first paragraph of each section (after h2)
  • paragraph alignment from the source (left / centre / justify) is preserved
  • empty "spacer" blocks are dropped — paragraph margins handle the rhythm
"""
import hashlib
import html
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
CONTENT = json.loads((ROOT / "content.json").read_text(encoding="utf-8"))
DOCS_DIR = ROOT / "docs"
OUT_DIR = DOCS_DIR / "content"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# (time, slug, title, content key = extracted/<slug>.xml) — must mirror docs/js/schedule.js.
SCHEDULE = [
    ("00:00", "01-miezonoptica",   "Miezonoptica",           "01-miezonoptica"),
    ("05:00", "02-utrenia",        "Utrenia",                "02-utrenia"),
    ("06:00", "03-ceasul-1",       "Ceasul Întâi",           "03-ceasul-1"),
    ("07:30", "04-mijloceasul-1",  "Mijloceasul Întâi",      "04-mijloceasul-1"),
    ("09:00", "05-ceasul-3",       "Ceasul al treilea",      "05-ceasul-3"),
    ("10:30", "06-mijloceasul-3",  "Mijloceasul al treilea", "06-mijloceasul-3"),
    ("12:00", "07-ceasul-6",       "Ceasul al șaselea",      "07-ceasul-6"),
    ("13:30", "08-mijloceasul-6",  "Mijloceasul al șaselea", "08-mijloceasul-6"),
    ("15:00", "09-ceasul-9",       "Ceasul al nouălea",      "09-ceasul-9"),
    ("16:30", "10-mijloceasul-9",  "Mijloceasul al nouălea", "10-mijloceasul-9"),
    ("18:00", "11-vecernia",       "Vecernia",               "11-vecernia"),
    ("21:00", "12-pavecernita",    "Pavecernița mică",       "12-pavecernita"),
]

# Per-service closing line. Romanian uses the genitive (Miezonopticii,
# Utreniei, Ceasului, …) so we map each slug explicitly. Appended at the
# end of the rendered page if the source docx doesn't already contain it.
ENDINGS = {
    "01-miezonoptica":  "Sfârșitul Miezonopticii.",
    "02-utrenia":       "Sfârșitul Utreniei.",
    "03-ceasul-1":      "Sfârșitul Ceasului Întâi.",
    "04-mijloceasul-1": "Sfârșitul Mijloceasului Întâi.",
    "05-ceasul-3":      "Sfârșitul Ceasului al treilea.",
    "06-mijloceasul-3": "Sfârșitul Mijloceasului al treilea.",
    "07-ceasul-6":      "Sfârșitul Ceasului al șaselea.",
    "08-mijloceasul-6": "Sfârșitul Mijloceasului al șaselea.",
    "09-ceasul-9":      "Sfârșitul Ceasului al nouălea.",
    "10-mijloceasul-9": "Sfârșitul Mijloceasului al nouălea.",
    "11-vecernia":      "Sfârșitul Vecerniei.",
    "12-pavecernita":   "Sfârșitul Pavecerniței mici.",
}

ALIGN_CLASS = {"center": "align-center", "both": "align-justify", "right": "align-right"}

# The doxology's opening phrase, also used to detect kyrie+doxology lines
# that the source docx fuses together on one line.
SLAVA_TATALUI = "Slavă Tatălui"

# Liturgical phrases that get a fixed style wherever they appear, regardless
# of the source docx formatting. Detected by paragraph-opening prefix.
SPECIAL_PHRASES = (
    ("Sfinte Dumnezeule",           "trisagion"),       # red bold centred
    (SLAVA_TATALUI,                 "doxology"),        # blue bold centred
    ("Și acum și pururea",          "doxology"),        # second half of the doxology
    ("și acum și pururea",          "doxology"),        # … sometimes lower-cased in source
    ("Doamne miluiește",            "kyrie"),           # red regular centred
    ("Doamne, miluiește",           "kyrie"),
    ("Dumnezeule, milostivește-Te", "versicle"),        # red bold centred
    ("Sfârșitul",                   "page-ending"),     # blue bold centred closing line
    ("Psalmul",                     "psalm-heading"),   # red bold centred heading-sized
)


def special_class(text):
    """Return the CSS class for a known liturgical phrase, or '' otherwise.
    The kyrie variants require a '(de N ori)' parenthetical so longer prayers
    that just happen to open with 'Doamne, miluiește-ne…' aren't captured."""
    for prefix, cls in SPECIAL_PHRASES:
        if text.startswith(prefix):
            if cls == "kyrie" and "(de " not in text:
                continue
            return cls
    return ""


def wrap_run(text_html, run):
    """Wrap already-escaped text in the run's formatting."""
    if run.get("color") == "red":
        text_html = f'<span class="rubric">{text_html}</span>'
    if run.get("italic"):
        text_html = f"<em>{text_html}</em>"
    if run.get("bold"):
        text_html = f"<strong>{text_html}</strong>"
    return text_html


def render_runs(runs, dropcap=False):
    """Render runs as inline HTML. If dropcap=True, the first letter of the
    first non-empty run is wrapped in <span class="dropcap">."""
    parts = []
    dropcap_pending = dropcap
    for run in runs:
        text = run.get("text", "")
        if not text:
            continue
        if dropcap_pending:
            # Find the first letter (skip whitespace and non-word chars at start).
            m = re.search(r"[^\W\d_]", text, flags=re.UNICODE)
            if m:
                lead, ch, rest = text[: m.start()], m.group(0), text[m.end() :]
                inner = (
                    html.escape(lead)
                    + f'<span class="dropcap">{html.escape(ch)}</span>'
                    + html.escape(rest)
                )
                parts.append(wrap_run(inner, run))
                dropcap_pending = False
                continue
        parts.append(wrap_run(html.escape(text), run))
    return "".join(parts)


def _is_duplicate_title(full_text, title_first_word):
    return full_text.lower().startswith(title_first_word) and len(full_text) < 90


def _try_split_kyrie_doxology(full_text):
    """If a paragraph fuses 'Doamne, miluiește …, Slavă Tatălui …' on one
    line, return (kyrie_text, doxology_text); otherwise None."""
    if not (full_text.startswith("Doamne") and SLAVA_TATALUI in full_text):
        return None
    idx = full_text.index(SLAVA_TATALUI)
    return full_text[:idx].rstrip(" ,."), full_text[idx:].strip()


def _try_split_kyrie_directive(full_text):
    """If a paragraph fuses 'Doamne, miluiește (de N ori)' with a rubric
    directive appended afterwards (e.g. 'Și troparele:'), split at the
    closing parenthesis so only the kyrie phrase carries the kyrie class."""
    if not full_text.startswith(("Doamne miluiește", "Doamne, miluiește")):
        return None
    paren_open = full_text.find("(de ")
    if paren_open == -1:
        return None
    paren_close = full_text.find(")", paren_open)
    if paren_close == -1:
        return None
    rest = full_text[paren_close + 1:].lstrip(" ,.")
    if not rest:
        return None
    return full_text[: paren_close + 1], rest


def _emit_heading(out, kind, runs, special):
    tag = "h2" if kind in ("h1", "h2") else "h3"
    cls = "align-center" + (f" {special}" if special else "")
    out.append(f'<{tag} class="{cls}">' + render_runs(runs) + f"</{tag}>")


def _emit_paragraph(out, runs, align, special, dropcap):
    """Emit a paragraph and return whether a drop-cap was actually used."""
    if special:
        cls, use_dropcap = special, False
    else:
        cls = ALIGN_CLASS.get(align, "")
        use_dropcap = dropcap
    inner = render_runs(runs, dropcap=use_dropcap)
    cls_attr = f' class="{cls}"' if cls else ""
    out.append(f"<p{cls_attr}>{inner}</p>")
    return use_dropcap


def _process_block(out, blk, state):
    """Handle one block: spacer/empty skip, first-title skip, kyrie+doxology
    split, then route to heading or paragraph emit. Mutates `state`."""
    kind = blk.get("kind")
    if kind == "spacer":
        return
    runs = blk.get("runs", [])
    full_text = "".join(r.get("text", "") for r in runs).strip()
    if not full_text:
        return

    if not state["skipped_first_title"] and kind in ("h1", "h2", "h3"):
        state["skipped_first_title"] = True
        if _is_duplicate_title(full_text, state["title_first_word"]):
            return

    split = _try_split_kyrie_doxology(full_text)
    if split:
        kyrie_text, doxology_text = split
        out.append(f'<p class="kyrie">{html.escape(kyrie_text)}</p>')
        out.append(f'<p class="doxology">{html.escape(doxology_text)}</p>')
        return

    split = _try_split_kyrie_directive(full_text)
    if split:
        kyrie_text, directive_text = split
        out.append(f'<p class="kyrie">{html.escape(kyrie_text)}</p>')
        out.append(f'<p>{html.escape(directive_text)}</p>')
        return

    special = special_class(full_text)
    if kind in ("h1", "h2", "h3"):
        _emit_heading(out, kind, runs, special)
        state["apply_dropcap"] = kind in ("h1", "h2")
        return

    all_red = bool(runs) and all(r.get("color") == "red" for r in runs)
    dropcap = state["apply_dropcap"] and not all_red and len(full_text) >= 6
    if _emit_paragraph(out, runs, blk.get("align"), special, dropcap):
        state["apply_dropcap"] = False


def render_blocks(blocks, page_title):
    """Render blocks for one page. Drops spacers and the first title-duplicate
    heading; emits drop-caps on the first paragraph of each section; routes
    known liturgical phrases through their fixed-style classes."""
    out = []
    state = {
        "skipped_first_title": False,
        "apply_dropcap": True,
        "title_first_word": page_title.lower().split()[0],
    }
    for blk in blocks:
        _process_block(out, blk, state)
    return "\n      ".join(out)


def _render_nav(cls, prev_slug, prev_title, next_slug, next_title):
    """Prev/next links between services; rendered above the title and again
    after the text so neither end of a long page is a dead end."""
    return f"""      <nav class="{cls}" aria-label="Navigare între ceasuri">
        <a href="{prev_slug}.html" rel="prev">← {html.escape(prev_title)}</a>
        <span class="spacer"></span>
        <a href="{next_slug}.html" rel="next">{html.escape(next_title)} →</a>
      </nav>"""


def render_page(slot_time, slug, title, docx_stem, prev_slug, prev_title, next_slug, next_title):
    blocks = CONTENT.get(docx_stem)
    if blocks is None:
        raise SystemExit(f"Missing content for {docx_stem!r}; have {list(CONTENT)}")
    body_html = render_blocks(blocks, title)
    # Append the canonical closing line if the source docx didn't include one.
    ending = ENDINGS.get(slug)
    if ending and "Sfârșitul" not in body_html:
        body_html += f'\n      <p class="page-ending">{html.escape(ending)}</p>'
    title_esc = html.escape(title)
    nav_top = _render_nav("page__nav page__nav--top", prev_slug, prev_title, next_slug, next_title)
    nav_bottom = _render_nav("page__nav", prev_slug, prev_title, next_slug, next_title)
    return f"""<!doctype html>
<html lang="ro">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title_esc} · Pravoslavnic</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Lora:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="../css/styles.css" />
</head>
<body>
  <article class="page">
    <div class="page__inner">
{nav_top}
      <div class="page__eyebrow">
        <span>Pravoslavnic</span>
        <span class="scheduled-time">{slot_time}</span>
      </div>
      <h1 class="page__title">{title_esc}</h1>
      <hr class="page__rule" />
      <div class="page__body">
      {body_html}
      </div>
      <div class="page__footer-mark" role="presentation" aria-hidden="true"></div>
{nav_bottom}
    </div>
  </article>
</body>
</html>
"""


def _docs_cache_version():
    """Content-derived cache version for the service worker. Hashes every
    file under docs/ except sw.js itself (would be self-referential) so a
    rebuild with no asset changes leaves the version untouched."""
    h = hashlib.sha256()
    paths = sorted(
        p for p in DOCS_DIR.rglob("*")
        if p.is_file() and p.name != "sw.js"
    )
    for p in paths:
        h.update(p.relative_to(DOCS_DIR).as_posix().encode("utf-8"))
        h.update(b"\0")
        h.update(p.read_bytes())
    return "v" + h.hexdigest()[:10]


def _update_sw_cache_version(version):
    """Rewrite `const CACHE_VERSION = "…"` in docs/sw.js to the given value.
    Returns True if the file changed."""
    sw = DOCS_DIR / "sw.js"
    text = sw.read_text(encoding="utf-8")
    new_text = re.sub(
        r'^(\s*const\s+CACHE_VERSION\s*=\s*")[^"]*(";)',
        r'\g<1>' + version + r'\g<2>',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if new_text == text:
        return False
    sw.write_text(new_text, encoding="utf-8")
    return True


def main():
    n = len(SCHEDULE)
    for i, (slot_time, slug, title, stem) in enumerate(SCHEDULE):
        prev = SCHEDULE[(i - 1) % n]
        nxt  = SCHEDULE[(i + 1) % n]
        html_doc = render_page(slot_time, slug, title, stem, prev[1], prev[2], nxt[1], nxt[2])
        path = OUT_DIR / f"{slug}.html"
        path.write_text(html_doc, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")

    # Refresh the service-worker cache version from a hash of all docs/ assets.
    # No-op if nothing changed since the last build.
    version = _docs_cache_version()
    if _update_sw_cache_version(version):
        print(f"bumped sw.js CACHE_VERSION → {version}")
    else:
        print(f"sw.js CACHE_VERSION already {version} (no change)")


if __name__ == "__main__":
    main()
