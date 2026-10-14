"""Offline reading desk with source observations and separate model candidates."""
import json
from pathlib import Path
from .observatory import check_bundle, check_review_events
from .observatory_facts import compare_values


def encode(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def render(bundle, reviews=None, run_status=None):
    check_bundle(bundle)
    events = check_review_events(bundle, reviews) if reviews is not None else []
    payload = {'bundle': bundle, 'reviews': events, 'run_status': run_status,
               'observations': {p['pair_id']: compare_values(p) for p in bundle['pairs']},
               # Preserve numeric representation: JS stringify changes 90.0 to 90.
               'bundle_export': json.dumps(bundle, ensure_ascii=False, indent=2, allow_nan=False),
               'desk_version': 'lis-evidence-desk-v2'}
    root = Path(__file__).resolve().parents[2] / 'zurich_pilot'
    text = (root / 'evidence_desk.html').read_text()
    script = (root / 'evidence_desk.js').read_text()
    if text.count('__DESK_DATA__') != 1 or text.count('__DESK_SCRIPT__') != 1:
        raise ValueError('invalid evidence-desk template')
    return text.replace('__DESK_SCRIPT__', script, 1).replace('__DESK_DATA__', encode(payload), 1)
