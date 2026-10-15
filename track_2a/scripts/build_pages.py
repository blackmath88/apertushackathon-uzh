"""Build an allowlisted, authored-only GitHub Pages demonstration. No network."""
import argparse
import json
from pathlib import Path
import tempfile
from uzh_rsd import federal_desk, federal_inventory

ROOT = Path(__file__).resolve().parents[1]

def build(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    # Never read campaign stores, captures, credentials or benchmark datasets.
    with tempfile.TemporaryDirectory() as tmp:
        fixture = Path(tmp) / 'fixture'
        federal_desk.demo(fixture)
        bundle = federal_desk.validate(json.loads((fixture / 'bundle.json').read_text()))
    assert bundle['fixture'] and bundle['analysis']['model_calls'] == 0
    payload = {'catalogue': federal_inventory.inventory(), 'bundle': bundle}
    encoded = json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c')
    template = (ROOT / 'web/pages/index.html').read_text()
    out.joinpath('index.html').write_text(template.replace('__PUBLIC_FIXTURE__', encoded))
    out.joinpath('app.js').write_text((ROOT / 'web/pages/app.js').read_text())
    out.joinpath('style.css').write_text((ROOT / 'web/pages/style.css').read_text())
    out.joinpath('.nojekyll').touch()
    return payload

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True)
    build(p.parse_args().out)
