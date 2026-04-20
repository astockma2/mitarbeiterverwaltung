"""
Rate-Limiter für Login-Versuche.

Nutzt Redis (Produktion) oder In-Memory-Dict (Entwicklung/Fallback).
Nach MAX_ATTEMPTS fehlgeschlagenen Versuchen innerhalb von WINDOW_SECONDS
wird die IP-Adresse für den Rest des Zeitfensters gesperrt.
"""

import asyncio
import logging
from collections import defaultdict
from time import time

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 900  # 15 Minuten

# In-Memory-Fallback (für Entwicklung oder wenn Redis nicht erreichbar ist)
_attempts: dict[str, list[float]] = defaultdict(list)
_lock = asyncio.Lock()


async def _get_redis():
    """Gibt einen verbundenen Redis-Client zurück, oder None bei Fehler."""
    try:
        import redis.asyncio as aioredis
        from app.config import get_settings

        settings = get_settings()
        client = aioredis.from_url(settings.redis_url, socket_connect_timeout=1)
        await client.ping()
        return client
    except Exception as e:
        logger.warning("Redis nicht verfügbar, nutze In-Memory-Fallback: %s", e)
        return None


async def is_rate_limited(identifier: str) -> tuple[bool, int]:
    """
    Prüft ob für den Identifier zu viele fehlgeschlagene Login-Versuche vorliegen.

    Returns:
        (is_blocked, retry_after_seconds): True + Wartezeit wenn gesperrt, sonst False + 0
    """
    r = await _get_redis()
    if r is not None:
        try:
            key = f"login_fail:{identifier}"
            count_raw = await r.get(key)
            if count_raw and int(count_raw) >= MAX_ATTEMPTS:
                ttl = await r.ttl(key)
                await r.aclose()
                return True, max(int(ttl), 1)
            await r.aclose()
            return False, 0
        except Exception as e:
            logger.warning("Redis-Fehler bei Rate-Limit-Prüfung: %s", e)

    # In-Memory-Fallback
    async with _lock:
        now = time()
        valid = [t for t in _attempts.get(identifier, []) if now - t < WINDOW_SECONDS]
        if len(valid) >= MAX_ATTEMPTS:
            oldest = valid[0]
            remaining = int(WINDOW_SECONDS - (now - oldest))
            return True, max(remaining, 1)
        return False, 0


async def record_failed_attempt(identifier: str) -> None:
    """Registriert einen fehlgeschlagenen Login-Versuch für den Identifier."""
    r = await _get_redis()
    if r is not None:
        try:
            key = f"login_fail:{identifier}"
            count = await r.incr(key)
            if count == 1:
                await r.expire(key, WINDOW_SECONDS)
            await r.aclose()
            return
        except Exception as e:
            logger.warning("Redis-Fehler beim Speichern des fehlgeschlagenen Versuchs: %s", e)

    # In-Memory-Fallback
    async with _lock:
        now = time()
        valid = [t for t in _attempts.get(identifier, []) if now - t < WINDOW_SECONDS]
        valid.append(now)
        _attempts[identifier] = valid


async def reset_failed_attempts(identifier: str) -> None:
    """Setzt den Fehlversuchs-Zähler nach erfolgreichem Login zurück."""
    r = await _get_redis()
    if r is not None:
        try:
            await r.delete(f"login_fail:{identifier}")
            await r.aclose()
            return
        except Exception as e:
            logger.warning("Redis-Fehler beim Zurücksetzen des Rate-Limits: %s", e)

    # In-Memory-Fallback
    async with _lock:
        _attempts.pop(identifier, None)
