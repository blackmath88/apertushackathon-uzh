"""Prompt construction for B0 (paper baseline) and B2 (difference spans).

B0 uses the published SwissGov-RSD admin templates
(``prompt_templates/template_{de,fr,it}_admin.txt``) at the pinned evaluator
commit. They are fetched at run time and hash-checked, like the evaluator,
because the upstream repository has no top-level licence (see SOURCES.md).

Documented B0 deviation (also in the technical report): the upstream
full-document script renders ``json.dumps(text)`` of the joined string, which
ASCII-escapes umlauts/accents; the template's own few-shot examples and the
upstream ``--short --llm`` path pass a JSON *token list*. We pass the token
list with non-ASCII characters unescaped, so the model sees the same format as
the few-shot examples and the benchmark tokens exactly.

B2 is our own zero-shot prompt (version ``B2_PROMPT_VERSION``). Only inference
inputs (no labels) are accepted by the builders.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from collections.abc import Callable
from pathlib import Path

from .data_adapter import TRACK_ROOT, InferenceInput
from .evaluation import OFFICIAL_COMMIT, OFFICIAL_REPO, OfficialEvaluatorUnavailable

B0_PROMPT_VERSION = "b0-paper-admin-template@1807a42/token-list-v1"
B2_PROMPT_VERSION = "b2-spans-v1"

OFFICIAL_PROMPTS = {
    "de": ("prompt_templates/template_de_admin.txt", "ace9e0f82646c182a2684573dad1faf7d73181cbb0aab7f0ee3b1f0b8be446c0"),
    "fr": ("prompt_templates/template_fr_admin.txt", "3d65ebd96ea3aea62f3fd1dceb127e825cef05357d1686228bafae3c84ded6e3"),
    "it": ("prompt_templates/template_it_admin.txt", "79e6cd0c9ae84d1fd33ddd3b94e5d69cae5608efacc3430ebf9043d6b316950a"),
}
DEFAULT_PROMPT_DIR = TRACK_ROOT / "data" / "official" / "swissgov-rsd" / OFFICIAL_COMMIT
LANGUAGE_NAMES = {"de": "German", "fr": "French", "it": "Italian"}


def fetch_prompts(dest: Path = DEFAULT_PROMPT_DIR, opener: Callable[..., object] = urllib.request.urlopen) -> Path:
    for relative, digest in OFFICIAL_PROMPTS.values():
        target = Path(dest) / relative
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == digest:
            continue
        url = f"https://raw.githubusercontent.com/{OFFICIAL_REPO}/{OFFICIAL_COMMIT}/{relative}"
        with opener(url, timeout=60) as response:  # type: ignore[operator]
            data = response.read()
        if hashlib.sha256(data).hexdigest() != digest:
            raise OfficialEvaluatorUnavailable(f"{url} does not match pinned sha256")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return Path(dest)


def load_b0_template(language: str, prompt_dir: Path = DEFAULT_PROMPT_DIR) -> str:
    relative, digest = OFFICIAL_PROMPTS[language]
    path = Path(prompt_dir) / relative
    if not path.exists():
        raise OfficialEvaluatorUnavailable(f"{path} missing; run `make s1-fetch`")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise OfficialEvaluatorUnavailable(f"{path} does not match pinned sha256")
    return data.decode("utf-8")


def render_b0(template: str, item: InferenceInput) -> str:
    """Render like jinja2 (single placeholders, one trailing newline dropped)."""
    for placeholder in ("{{ sentence1 }}", "{{ sentence2 }}"):
        if template.count(placeholder) != 1:
            raise ValueError(f"template must contain {placeholder} exactly once")
    if template.endswith("\n"):
        template = template[:-1]
    sentence1 = json.dumps(list(item.text_a.tokens), ensure_ascii=False)
    sentence2 = json.dumps(list(item.text_b.tokens), ensure_ascii=False)
    return template.replace("{{ sentence1 }}", sentence1).replace("{{ sentence2 }}", sentence2)


B2_TEMPLATE = """You compare two versions of the same Swiss government web page: an English version (A) and its {language} version (B). Both should carry the same information, but translation errors and unsynchronised updates introduce differences in meaning.

List every place where the meaning differs. For each difference give:
- "a": the words from A that are involved, copied exactly, or "" if the content exists only in B
- "b": the words from B that are involved, copied exactly, or "" if the content exists only in A
- "kind": "CHANGE" (both versions say something different), "OMISSION" (content of A is missing in B) or "ADDITION" (content of B is missing in A)
- "severity": an integer from 1 (slight nuance) to 5 (completely different or missing information)

Rules:
* Copy excerpts exactly as they appear below, including the spaces around punctuation. Keep each excerpt short (at most 15 words) and split longer passages into several differences.
* Ignore differences in wording, word order or grammar that keep the same meaning.
* If the two versions carry the same meaning, return {{"differences": []}}.
* Output only the raw JSON object, without any additional text: {{"differences": [{{"a": "...", "b": "...", "kind": "...", "severity": 3}}]}}

Version A (English):
{text_a}

Version B ({language}):
{text_b}"""


def render_b2(item: InferenceInput) -> str:
    return B2_TEMPLATE.format(
        language=LANGUAGE_NAMES[item.language],
        text_a=" ".join(item.text_a.tokens),
        text_b=" ".join(item.text_b.tokens),
    )


def prompt_sha256(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()
