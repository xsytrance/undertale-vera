"""Static serving — version-stamped assets so deploys never serve stale JS/CSS."""
import re

from fastapi.testclient import TestClient

import undertale_vera_app as appmod


client = TestClient(appmod.app)


def test_index_stamps_local_assets():
    r = client.get("/")
    assert r.status_code == 200
    # every local js/css reference carries a ?v= stamp derived from file mtime
    assert re.search(r'src="/js/app\.js\?v=\d+"', r.text)
    assert re.search(r'href="/css/determination\.css\?v=\d+"', r.text)
    # no unstamped local references remain
    assert not re.search(r'(?:src|href)="/(?:js|css)/[^"?]+"', r.text)
    # the HTML itself must revalidate every load — stale HTML would pin stale assets
    assert r.headers.get("cache-control") == "no-cache"


def test_stamped_assets_still_serve():
    r = client.get("/js/app.js?v=12345")
    assert r.status_code == 200 and "power" in r.text


def test_spa_fallback_also_stamped():
    r = client.get("/some/deep/route")
    assert r.status_code == 200
    assert re.search(r'src="/js/app\.js\?v=\d+"', r.text)
