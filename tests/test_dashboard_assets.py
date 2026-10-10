import os

DASH = os.path.join(os.path.dirname(__file__), "..", "dashboard")


def test_assets_exist():
    for name in ("index.html", "app.js", "serve.py", "README.md"):
        p = os.path.join(DASH, name)
        assert os.path.getsize(p) > 100, f"{name} missing/too small"


def test_app_js_uses_api_and_auth():
    js = open(os.path.join(DASH, "app.js")).read()
    assert "/api/state" in js and "/api/events" in js
    assert "localStorage" in js and "Authorization" in js


def test_serve_py_is_a_static_server():
    s = open(os.path.join(DASH, "serve.py")).read()
    assert "http.server" in s or "HTTPServer" in s
