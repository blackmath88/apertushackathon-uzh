"""Private, versioned source evidence. No model or benchmark dataset access.

Attribution: accessibility-red-team immutable capture/provenance principles.
HTML locations are character offsets in decoded UTF-8, not DOM byte offsets.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re

EXTRACTION_VERSION = "lis-main-blocks-v2"
TERMS_URL = "https://www.stadt-zuerich.ch/de/service/rechtliche-hinweise.html"
REUSE = {"status": "personal_use_only", "publication": "withheld_pending_rights_review",
         "terms_url": TERMS_URL, "german_authoritative": True}


def digest(value) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def write_new(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


@dataclass
class Node:
    tag: str
    attrs: dict
    path: str
    line: int
    column: int
    children: list = field(default_factory=list)


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
IGNORE = {"script", "style", "nav", "header", "footer", "aside", "form", "template",
          "stzh-header", "stzh-footer", "stzh-breadcrumb", "stzh-readspeaker", "stzh-pagebottom"}
BLOCK_TAGS = {"p", "li", "tr", "dt", "dd", "h1", "h2", "h3", "h4", "h5", "h6", "stzh-heading", "stzh-text", "stzh-clamp", "text_run", "attribute_text"}


class DocumentParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("document", {}, "", 1, 0)
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        parent = self.stack[-1]
        number = 1 + sum(isinstance(c, Node) and c.tag == tag for c in parent.children)
        line, column = self.getpos()
        node = Node(tag, dict(attrs), parent.path + f"/{tag}[{number}]", line, column)
        parent.children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        parent = self.stack[-1]
        line, column = self.getpos()
        number = 1 + sum(isinstance(c, Node) and c.tag == "text_run" for c in parent.children)
        parent.children.append(Node("text_run", {}, parent.path + f"/text()[{number}]", line, column, [data]))


def ignored(node):
    return (node.tag in IGNORE or "hidden" in node.attrs or
            node.attrs.get("aria-hidden") == "true")


def nodes(node):
    if ignored(node):
        return
    yield node
    for child in node.children:
        if isinstance(child, Node):
            yield from nodes(child)


def text_of(node):
    if ignored(node):
        return ""
    if node.tag == "br":
        return " "
    parts = [text_of(c) if isinstance(c, Node) else c for c in node.children]
    value = "".join(parts)
    if not value.strip() and node.tag == "stzh-link":
        value = node.attrs.get("label") or ""
    return value


def evidence_nodes(root):
    for n in nodes(root):
        yield n
        # Explicit audited attributes used by Zürich's server-rendered components.
        keys = []
        if n.tag == "stzh-contact":
            keys = ["main-heading", "heading", "city-label", "street", "street-info", "postal-code", "location", "numbers"]
        elif n.tag == "stzh-accordion-item":
            keys = ["heading"]
        elif n.tag == "stzh-datalist-item":
            keys = ["value"]
        for key in keys:
            value = n.attrs.get(key)
            if not value:
                continue
            if key in {"street", "street-info", "numbers"}:
                try:
                    raw = json.loads(value)
                    if not isinstance(raw, list):
                        continue
                    if key == "numbers":
                        value = "; ".join(str(v.get("label", "")) + " " + str(v.get("number", "")) for v in raw if isinstance(v, dict))
                    else:
                        value = "; ".join(v for v in raw if isinstance(v, str))
                except ValueError:
                    continue
            yield Node("attribute_text", {"source_attribute": key}, n.path + "/@" + key, n.line, n.column, [value])


def extract(html: bytes) -> dict:
    source = html.decode("utf-8", errors="strict")
    parser = DocumentParser()
    parser.feed(source)
    all_nodes = list(nodes(parser.root))
    mains = [n for n in all_nodes if n.tag == "main" or n.attrs.get("role") == "main"]
    if len(mains) != 1:
        return {"status": "unresolved", "reason": "requires_one_main_landmark", "text": "", "blocks": []}
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    blocks, pieces, cursor = [], [], 0
    for n in evidence_nodes(mains[0]):
        if n.tag not in BLOCK_TAGS:
            continue
        descendants = list(nodes(n))[1:]
        # Rows and list items retain their entire structure; wrappers are skipped
        # when narrower meaningful children exist. No duplicated paragraph text.
        if n.tag not in {"tr", "li"} and any(c.tag in BLOCK_TAGS - {"text_run"} for c in descendants):
            continue
        if any(n.path.startswith(b["locator"] + "/") for b in blocks):
            continue
        if n.tag == "tr":
            value = " | ".join(re.sub(r"\s+", " ", text_of(c)).strip()
                               for c in n.children if isinstance(c, Node) and c.tag in {"th", "td"})
        else:
            value = re.sub(r"\s+", " ", text_of(n)).strip()
        if not value:
            continue
        if pieces:
            cursor += 1
        kind = "heading" if n.tag.startswith("h") or n.tag == "stzh-heading" else (
            "table_row" if n.tag == "tr" else "list_item" if n.tag == "li" else "paragraph")
        block = {"id": f"block_{len(blocks)+1:04d}", "kind": kind, "text": value,
                 "start": cursor, "end": cursor + len(value), "locator": n.path,
                 "source_line": n.line, "source_column": n.column,
                 "source_character_start": offsets[n.line - 1] + n.column,
                 "source_attribute": n.attrs.get("source_attribute"),
                 "heading_level": n.attrs.get("level", n.tag[1:] if n.tag in {"h1","h2","h3","h4","h5","h6"} else None)}
        blocks.append(block)
        pieces.append(value)
        cursor += len(value)
    return {"status": "ok" if blocks else "unresolved", "reason": None if blocks else "no_meaningful_blocks",
            "text": "\n".join(pieces), "blocks": blocks}


def save_capture(root: Path, html: bytes, page) -> dict:
    result = extract(html)
    if sha256(html).hexdigest() != page.sha256_html:
        raise ValueError("source hash mismatch")
    capture_id = digest([page.url, page.retrieved_at_utc, page.sha256_html, EXTRACTION_VERSION])
    document = {"schema": "lost-in-switzerland/document/v1", "source_kind": "live_city_pilot",
                "capture_id": capture_id, "url": page.url, "title": page.title,
                "language": page.language, "retrieved_at_utc": page.retrieved_at_utc,
                "html_sha256": page.sha256_html, "text_sha256": sha256(result["text"].encode()).hexdigest(),
                "extraction_version": EXTRACTION_VERSION, "reuse": dict(REUSE), **result}
    document["record_digest"] = digest(document)
    raw_path = root / "html" / (page.sha256_html + ".html")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if raw_path.exists():
        if sha256(raw_path.read_bytes()).hexdigest() != page.sha256_html:
            raise ValueError("existing raw evidence corrupted")
    else:
        with raw_path.open("xb") as stream:
            stream.write(html)
    write_new(root / "documents" / (capture_id + ".json"), document)
    return {"capture_id": capture_id, "url": page.url, "language": page.language,
            "record_digest": document["record_digest"], "status": document["status"],
            "text_sha256": document["text_sha256"], "block_count": len(document["blocks"])}


def verify_document(document, root: Path | None = None):
    if document.get("schema") != "lost-in-switzerland/document/v1" or document.get("source_kind") != "live_city_pilot":
        raise ValueError("not pilot evidence")
    if digest({k: v for k, v in document.items() if k != "record_digest"}) != document["record_digest"]:
        raise ValueError("document record digest mismatch")
    if sha256(document["text"].encode()).hexdigest() != document["text_sha256"]:
        raise ValueError("text digest mismatch")
    if document["capture_id"] != digest([document["url"], document["retrieved_at_utc"], document["html_sha256"], document["extraction_version"]]):
        raise ValueError("capture identity mismatch")
    for block in document["blocks"]:
        if document["text"][block["start"]:block["end"]] != block["text"]:
            raise ValueError("block offset mismatch")
    if root is not None:
        raw = (root / "html" / (document["html_sha256"] + ".html")).read_bytes()
        if sha256(raw).hexdigest() != document["html_sha256"]:
            raise ValueError("HTML digest mismatch")
        if document["extraction_version"] != EXTRACTION_VERSION:
            raise ValueError("unsupported extraction revision")
        extracted = extract(raw)
        if any(document[k] != extracted[k] for k in ("text", "blocks", "status", "reason")):
            raise ValueError("extraction replay mismatch")
    return document
