"""Authored, offline server for the capture-preparation browser check. No network, no model."""
import json, sys, tempfile
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from uzh_rsd.campaign_center import Store, handler
from uzh_rsd.government_scout import FetchResponse

H = "https://www.bfe.admin.ch"; DE, FR = H + "/de/antrag", H + "/fr/demande"
PAGES = {DE: "<main><h1>Antrag</h1><p>Frist: 30 Tage</p></main>", FR: "<main><h1>Demande</h1><p>Délai: 20 jours</p></main>"}
fetch = lambda url, _p, **_k: FetchResponse(200, url, {"Content-Type": "text/html"}, PAGES[url].encode())
root = tempfile.mkdtemp(); store = Store(root, capture_fetcher=fetch); store.capture_fixture = True; store.capture_delay = 0
c = store.create("Capture fixture", site_ids=["bfe"])
langs = {"de": [{"url": DE}], "fr": [{"url": FR}], "it": [], "en": []}
snap = {"id": "a" * 32, "site_id": "bfe", "observed_at": "2026-10-14T00:00:00+00:00", "families": [{"family_id": "fam1", "status": "one_directional",
        "languages": langs, "edges": [], "language_availability": {k: "observed" if v else "not_observed" for k, v in langs.items()}}]}
(Path(root) / ("snapshot-" + snap["id"] + ".json")).write_text(json.dumps(snap))
d = store.read(c["id"]); d["discovery_runs"] = [{"id": "r", "state": "complete", "snapshot_id": snap["id"], "site_id": "bfe", "started_at": "2026-10-14T00:00:00+00:00", "stop_reason": "completed", "summary": {"families": 1, "candidates": 2, "unvisited": 0}, "progress": {}}]; store.write(d)
store.page_scope(c["id"], [{"snapshot_id": snap["id"], "family_id": "fam1"}])
server = ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8767), handler(store, "fixture-token"))
print(f"http://127.0.0.1:{server.server_port}", flush=True)
server.serve_forever()
