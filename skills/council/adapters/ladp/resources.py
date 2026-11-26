"""Load upstream personas and canonical rules, pin them in each room."""
import re
from pathlib import Path

from core.metadata import checksum
from core.storage import require

ROOT = Path(__file__).resolve().parent
SLUG = re.compile(r"[a-z][a-z0-9-]*\Z")


def source():
    # CLI installer copies unmodified upstream resources; plugin checkout uses
    # the repository's canonical originals. Neither is hand-maintained here.
    for root in (ROOT / "resources", ROOT.parents[3]):
        if (root / "SKILL.md").is_file() and (root / "agents").is_dir():
            return root
    raise ValueError("canonical Council resources missing; reinstall Council")


def roster():
    root = source()
    return sorted(p.stem.removeprefix("council-") for p in
                  (root / "agents").glob("council-*.md"))


def section(text, prefix):
    # The verdict templates contain Markdown headings inside fenced examples.
    # Only canonical step/template headings delimit the source sections.
    headings = list(re.finditer(
        r"^(?:### (?:(?:QUICK |DUO )?STEP [0-9.]+:|Council Verdict \(Full Mode\)|Quick Verdict|Duo Verdict)|"
        r"## (?:Quick Mode Sequence|Duo Mode Sequence|Output Templates|Example Usage)).*$",
        text, re.MULTILINE))
    for i, match in enumerate(headings):
        if match.group(0).startswith("### " + prefix):
            stop = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            return text[match.start():stop].strip()
    raise ValueError("incompatible upstream protocol: missing section " + prefix)


def pin(seats):
    root = source()
    rules = (root / "SKILL.md").read_text(encoding="utf-8")
    for title in ("STEP 1.5:", "STEP 2:", "STEP 3:", "STEP 4:", "STEP 5:",
                  "STEP 6:", "STEP 7:", "QUICK STEP 1:", "QUICK STEP 2:",
                  "DUO STEP 1:", "DUO STEP 2:", "DUO STEP 3:",
                  "Council Verdict (Full Mode)", "Quick Verdict", "Duo Verdict"):
        section(rules, title)
    require(len(seats) == len(set(seats)), "duplicate seats")
    personas, methods = {}, set()
    for seat in seats:
        require(SLUG.fullmatch(seat) and seat in roster(), "unknown Council seat: " + seat)
        text = (root / "agents" / ("council-" + seat + ".md")).read_text(encoding="utf-8")
        method = re.search(r"^  reasoning_method:\s*([^\r\n]+)$", text, re.MULTILINE)
        require(method is not None, "missing reasoning method: " + seat)
        value = method.group(1).strip()
        require(value not in methods, "duplicate reasoning method: " + value)
        methods.add(value)
        personas[seat] = text
    return {"rules": rules, "personas": personas}


def rules_for(resource, mode, phase, coordinator=False):
    text = resource["rules"]
    if phase == "restate":
        titles = ["STEP 1.5:"]
    elif phase == "commit":
        if mode == "full":
            block = section(text, "STEP 2:")
            marker = "**Prompt template**"
            require(marker in block, "upstream analysis prompt missing")
            return block[block.index(marker):].split("**Note**:", 1)[0]
        titles = ["QUICK STEP 1:" if mode == "quick" else "DUO STEP 1:"]
    elif phase == "debate":
        titles = ["STEP 3:" if mode == "full" else "DUO STEP 2:"]
        if coordinator and mode == "full":
            titles.append("STEP 4:")
    elif phase == "enforce":
        titles = ["STEP 4:"]
    elif phase == "position":
        titles = [{"full": "STEP 5:", "quick": "QUICK STEP 2:", "duo": "DUO STEP 3:"}[mode]]
        if coordinator and mode != "duo":
            titles.append("STEP 6:")
    elif phase == "synthesis":
        titles = [{"full": "Council Verdict (Full Mode)", "quick": "Quick Verdict",
                   "duo": "Duo Verdict"}[mode]]
    else:
        return ""
    return "\n\n".join(section(text, title) for title in titles)


def anonymize(content, seat, persona, label):
    """Best-effort removal of explicit self-attribution, not a security boundary."""
    figure = re.search(r"^  figure:\s*(.+)$", persona, re.MULTILINE)
    names = ["council-" + seat]
    if figure:
        names.append(figure.group(1).strip().strip('"\''))
    for name in names:
        content = re.sub(r"(?im)^(\s*#{0,6}\s*\*{0,2})" + re.escape(name)
                         + r"(?=\s*(?:[:—–-]|\*{0,2}\s*$))", r"\g<1>" + label, content)
        content = re.sub(r"(?i)\bAs\s+" + re.escape(name) + r"\b", "As " + label, content)
    return content
