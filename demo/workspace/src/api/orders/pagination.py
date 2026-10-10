"""Orders API pagination.

Team decision (see Keel): the orders API uses CURSOR-based pagination.
Edit this file during the demo to trigger Keel's PreToolUse check.
"""


def list_orders(cursor: str | None = None, limit: int = 50):
    """Return a page of orders using an opaque cursor (cursor-based pagination)."""
    # ... fetch `limit` rows after `cursor`, return (rows, next_cursor)
    raise NotImplementedError
