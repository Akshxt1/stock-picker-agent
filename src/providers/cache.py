from datetime import datetime, timedelta, timezone

from src.database.models import MarketDataCache, Session, init_db


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_cached(cache_key: str):
    init_db()
    with Session() as sess:
        row = sess.get(MarketDataCache, cache_key)
        if not row or not row.expires_at or row.expires_at <= _now():
            return None
        return row.payload


def set_cached(cache_key: str, source: str, payload: dict, ttl_seconds: int):
    init_db()
    expires_at = _now() + timedelta(seconds=ttl_seconds)
    with Session() as sess:
        row = sess.get(MarketDataCache, cache_key)
        if row:
            row.source = source
            row.payload = payload
            row.expires_at = expires_at
        else:
            row = MarketDataCache(
                cache_key=cache_key,
                source=source,
                payload=payload,
                expires_at=expires_at,
            )
            sess.add(row)
        sess.commit()
