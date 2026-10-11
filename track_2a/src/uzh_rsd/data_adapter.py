"""Development-only SwissGov-RSD adapter.

Source: Hugging Face dataset ``ZurichNLP/SwissGov-RSD`` pinned to an exact
revision. Only the per-language ``dev`` files are registered. The dataset has
no ``train`` file and the ``test`` files are deliberately absent from this
module: no URL, path or hash for them exists here.

Every public entry point calls :func:`assert_development_split` before it
builds a path, touches the filesystem or opens a network connection.

Inference inputs and gold labels are returned as separate objects. Inference
objects carry no label fields, so gold cannot leak into prompts by accident.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from .splits import assert_development_split
from .tokens import TokenizedText, check_vector, tokenize

DATASET_REPO = "ZurichNLP/SwissGov-RSD"
DATASET_REVISION = "f16aa0536811b8c0cf975fede21eec5996e4b3c1"
DATASET_LICENSE = "Labels CC BY 4.0; text copyright Swiss federal authorities (see dataset LICENSE.md)"
LANGUAGES = ("de", "fr", "it")
TRACK_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = TRACK_ROOT / "data" / "raw"

REQUIRED_FIELDS = ("id", "text_a", "text_b", "labels_a", "labels_b", "page_en", "page_other", "subset")


@dataclass(frozen=True)
class PinnedFile:
    path: str
    git_oid: str
    size: int


# Hugging Face tree API at DATASET_REVISION (plain git blobs, not LFS).
_SPLIT_FILES: dict[str, dict[str, PinnedFile]] = {
    "dev": {
        "de": PinnedFile("data/de/dev_de.jsonl", "3f1fba69325ee5ad933064cb53be22739925fa56", 2300724),
        "fr": PinnedFile("data/fr/dev_fr.jsonl", "07ad1df22a4a69b043e4b477dff030ab2e261e9e", 2489668),
        "it": PinnedFile("data/it/dev_it.jsonl", "991e5aeb51761d256d51010976d0296b5551d6e5", 2387999),
    },
}


class SplitUnavailableError(LookupError):
    """The split is permitted by policy but no official source file exists."""


class IntegrityError(ValueError):
    """Downloaded or cached bytes do not match the pinned revision."""


@dataclass(frozen=True)
class InferenceInput:
    """Everything a model may see. Deliberately has no label fields."""

    id: str
    language: str
    text_a: TokenizedText
    text_b: TokenizedText
    page_en: str
    page_other: str

    @property
    def pair(self) -> str:
        return f"en-{self.language}"

    @property
    def doc_index(self) -> int:
        return int(self.id.rsplit("_", 1)[1])


@dataclass(frozen=True)
class GoldLabels:
    """Evaluation-only object. Never pass to a prompt builder."""

    id: str
    labels_a: tuple[float, ...]
    labels_b: tuple[float, ...]


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _resolve(split: str, language: str) -> PinnedFile:
    assert_development_split(split)
    if language not in LANGUAGES:
        raise ValueError(f"Unsupported language {language!r}; expected one of {LANGUAGES}")
    files = _SPLIT_FILES.get(split)
    if files is None:
        raise SplitUnavailableError(
            f"No official {split!r} file exists in {DATASET_REPO}@{DATASET_REVISION}; "
            "only 'dev' is published for development."
        )
    return files[language]


def local_path(split: str, language: str, data_dir: Path = DEFAULT_DATA_DIR) -> Path:
    pinned = _resolve(split, language)
    return Path(data_dir) / "swissgov-rsd" / DATASET_REVISION / pinned.path


def source_url(split: str, language: str) -> str:
    pinned = _resolve(split, language)
    return f"https://huggingface.co/datasets/{DATASET_REPO}/resolve/{DATASET_REVISION}/{pinned.path}"


def _verify(data: bytes, pinned: PinnedFile, origin: str) -> None:
    if len(data) != pinned.size or git_blob_sha1(data) != pinned.git_oid:
        raise IntegrityError(f"{origin} does not match pinned {pinned.path}@{DATASET_REVISION}")


def fetch_split(
    split: str,
    language: str,
    data_dir: Path = DEFAULT_DATA_DIR,
    opener: Callable[..., object] = urllib.request.urlopen,
    timeout: float = 60.0,
) -> Path:
    """Download exactly one pinned dev file (if not cached) and verify it."""
    pinned = _resolve(split, language)
    target = local_path(split, language, data_dir)
    if target.exists():
        _verify(target.read_bytes(), pinned, str(target))
        return target
    url = source_url(split, language)
    with opener(url, timeout=timeout) as response:  # type: ignore[operator]
        data = response.read()
    _verify(data, pinned, url)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
        handle.write(data)
        temporary = handle.name
    os.replace(temporary, target)
    return target


def _parse(raw: Mapping[str, object], language: str, line_number: int) -> tuple[InferenceInput, GoldLabels]:
    missing = [field for field in REQUIRED_FIELDS if field not in raw]
    if missing:
        raise ValueError(f"line {line_number}: missing fields {missing}")
    record_id = raw["id"]
    if not isinstance(record_id, str) or not record_id.startswith(f"admin_{language}_"):
        raise ValueError(f"line {line_number}: unexpected id {record_id!r} for language {language}")
    text_a = tokenize(raw["text_a"])  # type: ignore[arg-type]
    text_b = tokenize(raw["text_b"])  # type: ignore[arg-type]
    labels_a = check_vector(text_a, raw["labels_a"], name=f"{record_id}.labels_a", allow_mask=True)  # type: ignore[arg-type]
    labels_b = check_vector(text_b, raw["labels_b"], name=f"{record_id}.labels_b", allow_mask=True)  # type: ignore[arg-type]
    inference = InferenceInput(
        id=record_id,
        language=language,
        text_a=text_a,
        text_b=text_b,
        page_en=str(raw["page_en"]),
        page_other=str(raw["page_other"]),
    )
    return inference, GoldLabels(id=record_id, labels_a=labels_a, labels_b=labels_b)


def load_split(split: str, language: str, data_dir: Path = DEFAULT_DATA_DIR) -> list[tuple[InferenceInput, GoldLabels]]:
    """Load a verified local copy. Never downloads; run ``fetch_split`` first."""
    pinned = _resolve(split, language)
    path = local_path(split, language, data_dir)
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run `make s1-fetch` (downloads dev only)")
    data = path.read_bytes()
    _verify(data, pinned, str(path))
    records = []
    seen: set[str] = set()
    for line_number, line in enumerate(data.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = _parse(json.loads(line), language, line_number)
        if record[0].id in seen:
            raise ValueError(f"duplicate id {record[0].id}")
        seen.add(record[0].id)
        records.append(record)
    return records


# --- fixed dev manifest -----------------------------------------------------

MANIFEST_RULE_VERSION = "s1-dev-manifest-v1"
MANIFEST_DOCS = 3
# Gold-blind feasibility bound on whitespace tokens per side (text only).
MANIFEST_MAX_TOKENS_PER_SIDE = 400
MANIFEST_MIN_TOKENS_PER_SIDE = 40


def _rank_key(doc_index: int) -> str:
    return hashlib.sha256(f"{MANIFEST_RULE_VERSION}|{doc_index}".encode()).hexdigest()


def select_manifest_docs(inputs_by_language: Mapping[str, Iterable[InferenceInput]], excluded_ids: Iterable[str]) -> list[int]:
    """Pick document indices without looking at gold labels.

    Rule: documents present in all three dev files, none of whose ids appear in
    the official ``list_to_drop.txt``, every side within the token bounds; then
    order by sha256(rule-version|index) and take the first ``MANIFEST_DOCS``.
    """
    excluded = set(excluded_ids)
    by_language = {language: {item.doc_index: item for item in items} for language, items in inputs_by_language.items()}
    if set(by_language) != set(LANGUAGES):
        raise ValueError("manifest selection needs de, fr and it inputs")
    common = set.intersection(*(set(indexed) for indexed in by_language.values()))

    def eligible(index: int) -> bool:
        for language in LANGUAGES:
            item = by_language[language][index]
            if item.id in excluded:
                return False
            for side in (item.text_a, item.text_b):
                if not MANIFEST_MIN_TOKENS_PER_SIDE <= len(side) <= MANIFEST_MAX_TOKENS_PER_SIDE:
                    return False
        return True

    chosen = sorted((index for index in common if eligible(index)), key=_rank_key)[:MANIFEST_DOCS]
    if len(chosen) < MANIFEST_DOCS:
        raise ValueError(f"only {len(chosen)} eligible documents; manifest needs {MANIFEST_DOCS}")
    return chosen


def build_manifest(records_by_language: Mapping[str, list[tuple[InferenceInput, GoldLabels]]], excluded_ids: Iterable[str], excluded_ids_sha256: str) -> dict:
    inputs_by_language = {language: [inference for inference, _ in records] for language, records in records_by_language.items()}
    chosen = select_manifest_docs(inputs_by_language, excluded_ids)
    entries = []
    for language in LANGUAGES:
        lookup = {inference.doc_index: (inference, gold) for inference, gold in records_by_language[language]}
        for index in chosen:
            inference, gold = lookup[index]
            entries.append(
                {
                    "id": inference.id,
                    "pair": inference.pair,
                    "doc_index": index,
                    "page_en": inference.page_en,
                    "page_other": inference.page_other,
                    "tokens_a": len(inference.text_a),
                    "tokens_b": len(inference.text_b),
                    "text_a_sha256": inference.text_a.sha256,
                    "text_b_sha256": inference.text_b.sha256,
                    "gold_sha256": hashlib.sha256(json.dumps([gold.labels_a, gold.labels_b]).encode()).hexdigest(),
                }
            )
    body = {
        "schema": "uzh-rsd.dev-manifest/v1",
        "rule": {
            "version": MANIFEST_RULE_VERSION,
            "documents": MANIFEST_DOCS,
            "tokens_per_side": [MANIFEST_MIN_TOKENS_PER_SIDE, MANIFEST_MAX_TOKENS_PER_SIDE],
            "excluded_ids_source": "SwissGov-RSD list_to_drop.txt",
            "excluded_ids_sha256": excluded_ids_sha256,
            "ordering": "sha256('<version>|<doc_index>') ascending; gold labels not consulted",
        },
        "split": "dev",
        "dataset": {
            "repo": DATASET_REPO,
            "revision": DATASET_REVISION,
            "files": {language: {"path": f.path, "git_oid": f.git_oid, "size": f.size} for language, f in _SPLIT_FILES["dev"].items()},
        },
        "counts": {f"en-{language}": sum(1 for entry in entries if entry["pair"] == f"en-{language}") for language in LANGUAGES},
        "entries": entries,
    }
    body["manifest_sha256"] = manifest_digest(body)
    return body


def manifest_digest(manifest: Mapping[str, object]) -> str:
    content = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
