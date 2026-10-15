"""Public build must be deterministic, authored-only and offline."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_pages', ROOT / 'scripts/build_pages.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

class PagesBuildTest(unittest.TestCase):
    def test_allowlisted_offline_reproducible_build(self):
        with tempfile.TemporaryDirectory() as tmp, patch('socket.socket', side_effect=AssertionError('network forbidden')):
            a, b = Path(tmp)/'a', Path(tmp)/'b'
            payload = builder.build(a)
            builder.build(b)
            self.assertTrue(payload['bundle']['fixture'])
            self.assertEqual(payload['bundle']['analysis']['model_calls'], 0)
            self.assertEqual({p.name for p in a.iterdir()}, {'index.html','app.js','style.css','.nojekyll'})
            for p in a.iterdir(): self.assertEqual(p.read_bytes(), (b/p.name).read_bytes())
            html = (a/'index.html').read_text()
            self.assertNotIn('__PUBLIC_FIXTURE__', html)
            self.assertIn("connect-src 'none'", html)
            self.assertNotIn('__SESSION_TOKEN__', html)
            self.assertNotIn('/api/campaigns', (a/'app.js').read_text())
            self.assertEqual(len(payload['catalogue']['sites']), 34)

if __name__ == '__main__': unittest.main()
