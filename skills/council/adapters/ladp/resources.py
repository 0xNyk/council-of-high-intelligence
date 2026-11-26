"""Load upstream personas and canonical rules, pin them in each room."""
import json
import re
import protocol
from pathlib import Path

from ladp_core.metadata import checksum
from ladp_core.storage import require

ROOT = Path(__file__).resolve().parent
SLUG = re.compile(r"[a-z][a-z0-9-]*\Z")


def source():
    # CLI installer copies unmodified upstream resources; plugin checkout uses
    # the repository's canonical originals. Neither is hand-maintained here.
    candidates = [ROOT / "resources"] + list(ROOT.parents)[3:4]
    for root in candidates:
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


# The upstream Markdown is not a versioned API. Approve all phase-relevant
# source sections together rather than silently accepting changed semantics.
CONTRACT_SECTIONS = (
    "STEP 0:", "STEP 1.5:", "STEP 1.7:", "STEP 2:", "STEP 3:", "STEP 4:",
    "STEP 5:", "STEP 6:", "STEP 7:", "STEP 8:", "QUICK STEP 0:",
    "QUICK STEP 0.5:", "QUICK STEP 1:", "QUICK STEP 2:", "QUICK STEP 3:",
    "DUO STEP 0:", "DUO STEP 0.5:", "DUO STEP 1:", "DUO STEP 2:",
    "DUO STEP 3:", "DUO STEP 4:", "Council Verdict (Full Mode)",
    "Quick Verdict", "Duo Verdict",
)


def contract_hash(rules):
    return checksum({title: section(rules, title) for title in CONTRACT_SECTIONS})


def pin(seats, policy_version, config=None):
    config = protocol.load() if config is None else protocol.validate(config)
    root = source()
    rules = (root / "SKILL.md").read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))
    contract = contract_hash(rules)
    require(manifest["schema"] == 1 and
            manifest["reviewed_contracts"].get(contract, {}).get("policy_version") == policy_version,
            "upstream Council protocol changed; review adapter compatibility before creating rooms")
    require(len(seats) == len(set(seats)), "duplicate seats")
    personas, methods = {}, set()
    available = set(roster())
    for seat in seats:
        require(SLUG.fullmatch(seat) and seat in available, "unknown Council seat: " + seat)
        text = (root / "agents" / ("council-" + seat + ".md")).read_text(encoding="utf-8")
        method = re.search(r"^  reasoning_method:\s*([^\r\n]+)$", text, re.MULTILINE)
        require(method is not None, "missing reasoning method: " + seat)
        value = method.group(1).strip()
        require(value not in methods, "duplicate reasoning method: " + value)
        methods.add(value)
        personas[seat] = text
    # Freeze exact rendered references rather than reinterpreting old Markdown
    # with a newer section parser when an existing room resumes.
    references = {}
    for mode in ("full", "quick", "duo"):
        for phase in ("restate", "commit", "debate", "enforce", "position", "synthesis"):
            for host in (False, True):
                key = reference_key(mode, phase, host)
                references[key] = extract_reference(rules, mode, phase, host, config["modes"][mode]["stages"])
    return {"contract_hash": contract, "personas": personas, "references": references,
            "protocol": config}


def reference_key(mode, phase, coordinator):
    return ":".join((mode, phase, "host" if coordinator else "member"))


def rules_for(resource, mode, phase, coordinator=False):
    return resource["references"].get(reference_key(mode, phase, coordinator), "")


def extract_reference(text, mode, phase, coordinator, stages):
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
        if coordinator and mode == "full" and "enforcement" in stages:
            titles.append("STEP 4:")
    elif phase == "enforce":
        titles = ["STEP 4:"]
    elif phase == "position":
        titles = [{"full": "STEP 5:", "quick": "QUICK STEP 2:", "duo": "DUO STEP 3:"}[mode]]
        if coordinator and mode != "duo":
            titles.append("STEP 6:")
    elif phase == "synthesis":
        titles = [{"full": "STEP 7:", "quick": "QUICK STEP 3:", "duo": "DUO STEP 4:"}[mode],
                  {"full": "Council Verdict (Full Mode)", "quick": "Quick Verdict",
                   "duo": "Duo Verdict"}[mode]]
    else:
        return ""
    return "\n\n".join(section(text, title) for title in titles)


def anonymize(content, seat, persona, label):
    """Best-effort removal of explicit self-attribution, not a security boundary."""
    figure = re.search(r"^  figure:\s*(.+)$", persona, re.MULTILINE)
    names = ["council-" + seat, seat]
    if figure:
        names.append(figure.group(1).strip().strip('"\''))
    for name in names:
        content = re.sub(r"(?im)^(\s*#{0,6}\s*\*{0,2})" + re.escape(name)
                         + r"(?=\s*(?:[:—–-]|\*{0,2}\s*$))", r"\g<1>" + label, content)
        content = re.sub(r"(?i)\b(As|by)\s+" + re.escape(name) + r"\b", lambda m: m.group(1) + " " + label, content)
    return content
