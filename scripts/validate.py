"""Check packaging, local links, and synthetic PayTR HMAC vectors offline."""

import base64
import hashlib
import hmac
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent.parent


def check_vectors(root: Path) -> list[str]:
    errors: list[str] = []
    references = root / "skills/paytr/references"
    cases = (
        ("iframe-integration.md", "paytr_token", "merchant_id user_ip merchant_oid email payment_amount user_basket no_installment max_installment currency test_mode merchant_salt"),
        ("callbacks-settlement.md", "hash", "merchant_oid merchant_salt status total_amount"),
        ("inquiry-refunds.md", "paytr_token", "merchant_id merchant_oid merchant_salt"),
        ("inquiry-refunds.md", "paytr_token", "merchant_id merchant_oid return_amount merchant_salt"),
    )
    offsets: dict[str, int] = {}
    for filename, signature, ordered_fields in cases:
        path = references / filename
        if not path.is_file():
            errors.append(f"Missing vector reference: {filename}")
            continue
        text = path.read_text(encoding="utf-8")
        blocks = re.findall(r"Synthetic check vector, for offline tests only:\s*```text\s*\n(.*?)```", text, re.S)
        index = offsets.get(filename, 0)
        offsets[filename] = index + 1
        if index >= len(blocks):
            errors.append(f"{filename}: missing synthetic vector {index + 1}")
            continue
        fields = dict(re.findall(r"\b([a-z_]+)=(\S+)", blocks[index]))
        try:
            if "user_basket" in fields:
                basket = json.dumps([["Test ürünü", "12.34", 1]], ensure_ascii=False, separators=(",", ":"))
                if fields["user_basket"] != base64.b64encode(basket.encode("utf-8")).decode("ascii"):
                    errors.append(f"{filename}: Unicode basket vector differs")
            message = "".join(fields[name] for name in ordered_fields.split())
            digest = hmac.new(fields["merchant_key"].encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
            if not hmac.compare_digest(base64.b64encode(digest).decode("ascii"), fields[signature]):
                errors.append(f"{filename}: HMAC vector {index + 1} differs")
        except KeyError as missing:
            errors.append(f"{filename}: missing vector field {missing.args[0]}")
    return errors


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    skills = sorted((root / "skills").glob("*/SKILL.md"))
    if not skills:
        errors.append("No skills/*/SKILL.md found")

    for required in ("README.md", "LICENSE", "AGENTS.md", "evals/scenarios.md"):
        if not (root / required).is_file():
            errors.append(f"Missing {required}")

    for skill in skills:
        text = skill.read_text(encoding="utf-8")
        frontmatter = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
        if not frontmatter:
            errors.append(f"{skill.relative_to(root)}: missing YAML frontmatter")
            continue
        fields = frontmatter.group(1)
        name = re.search(r"^name:\s*([a-z0-9-]+)\s*$", fields, re.M)
        description = re.search(r"^description:\s*\S", fields, re.M)
        if not name or name.group(1) != skill.parent.name or len(name.group(1)) > 64:
            errors.append(f"{skill.relative_to(root)}: name must match folder")
        if not description:
            errors.append(f"{skill.relative_to(root)}: description is required")
        if re.search(r"\[TODO\b|\[INSERT\b", text):
            errors.append(f"{skill.relative_to(root)}: unfinished scaffold")

    for document in sorted(root.rglob("*.md")):
        if ".git" in document.relative_to(root).parts:
            continue
        text = document.read_text(encoding="utf-8")
        # Ignore examples inside fenced code; inspect inline and reference links.
        text = re.sub(r"^```[^\n]*\n.*?^```[^\n]*(?:\n|$)", "", text, flags=re.M | re.S)
        links = re.findall(r"\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)", text)
        links += re.findall(r"^\[[^\]]+\]:\s*(\S+)", text, flags=re.M)
        for link in links:
            target = urlsplit(link.strip("<>"))
            if target.scheme or target.netloc or not target.path:
                continue
            resolved = (document.parent / unquote(target.path)).resolve()
            if not resolved.is_relative_to(root.resolve()):
                errors.append(f"{document.relative_to(root)}: link escapes repository: {link}")
            elif not resolved.exists():
                errors.append(f"{document.relative_to(root)}: broken local link: {link}")
    return errors


if __name__ == "__main__":
    failures = validate(ROOT) + check_vectors(ROOT)
    if failures:
        print("\n".join(f"ERROR: {failure}" for failure in failures), file=sys.stderr)
        sys.exit(1)
    print("Skill packaging, local Markdown links, and 4 synthetic HMAC vectors: OK (offline)")
