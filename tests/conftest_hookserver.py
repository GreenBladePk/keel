import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest_asyncio

from keel.db import pool as db


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _test_dsn() -> str:
    return os.environ.get("KEEL_TEST_DATABASE_URL",
                          "postgresql://keel:keel@localhost:5433/keel_test")


@pytest_asyncio.fixture
async def hook_server():
    """Launch the real Keel server as a subprocess bound to the test DB, yield
    (mcp_url, token). The hook scripts curl this URL exactly as they would a real
    deployment."""
    port = _free_port()
    dsn = _test_dsn()
    # ensure schema exists before the server (and the hooks) touch it
    pool = await db.init_pool(dsn)
    async with pool.acquire() as c:
        await db.apply_schema(c)
    await db.close_pool()
    # config.get_settings reads DATABASE_URL (not KEEL_DATABASE_URL) for the dsn
    env = {**os.environ, "DATABASE_URL": dsn, "KEEL_LLM_PROVIDER": "none",
           "PORT": str(port)}
    proc = subprocess.Popen([sys.executable, "-m", "keel.server"], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    up = False
    for _ in range(100):
        try:
            urllib.request.urlopen(base + "/mcp", data=b"{}", timeout=0.5)
        except urllib.error.HTTPError:
            up = True  # an HTTP response (401) means the server is answering
            break
        except Exception:
            time.sleep(0.1)
    if not up:
        proc.terminate()
        raise RuntimeError("hook_server did not start")
    try:
        yield base + "/mcp", "dev-token"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
