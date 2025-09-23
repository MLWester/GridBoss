from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Literal

import redis

logger = logging.getLogger("app.idempotency")

IdempotencyResult = Literal["claimed", "duplicate", "conflict"]


@dataclass
class IdempotencyConfig:
    redis_url: str
    ttl_seconds: int = 600


class IdempotencyService:
    def __init__(self, config: IdempotencyConfig) -> None:
        self.config = config
        self._redis_client: redis.Redis | None = None
        self._memory_store: dict[str, tuple[str, float]] = {}

        try:
            self._redis_client = redis.Redis.from_url(config.redis_url, decode_responses=True)
            self._redis_client.ping()
        except Exception as exc:  # pragma: no cover - fallback path
            logger.warning("Idempotency Redis connection failed: %s -- using in-memory store", exc)
            self._redis_client = None

    def _build_key(self, scope: str, key: str) -> str:
        return f"idempotency:{scope}:{key}".lower()

    @staticmethod
    def _hash_payload(raw_payload: str) -> str:
        return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

    def claim(self, *, scope: str, key: str, payload_hash: str) -> IdempotencyResult:
        storage_key = self._build_key(scope, key)
        if self._redis_client is not None:
            return self._claim_redis(storage_key, payload_hash)
        return self._claim_memory(storage_key, payload_hash)

    def release(self, *, scope: str, key: str) -> None:
        storage_key = self._build_key(scope, key)
        if self._redis_client is not None:
            try:
                self._redis_client.delete(storage_key)
            except redis.RedisError:  # pragma: no cover - best effort cleanup
                logger.warning("Failed to release idempotency key %s", storage_key)
        else:
            self._memory_store.pop(storage_key, None)

    def _claim_redis(self, storage_key: str, payload_hash: str) -> IdempotencyResult:
        assert self._redis_client is not None
        try:
            was_created = self._redis_client.set(
                storage_key,
                payload_hash,
                nx=True,
                ex=self.config.ttl_seconds,
            )
        except redis.RedisError as exc:  # pragma: no cover
            logger.warning("Redis error recording idempotency: %s", exc)
            return self._claim_memory(storage_key, payload_hash)

        if was_created:
            return "claimed"

        try:
            existing = self._redis_client.get(storage_key)
        except redis.RedisError as exc:  # pragma: no cover
            logger.warning("Redis error fetching idempotency: %s", exc)
            return self._claim_memory(storage_key, payload_hash)

        if existing == payload_hash:
            return "duplicate"
        return "conflict"

    def _claim_memory(self, storage_key: str, payload_hash: str) -> IdempotencyResult:
        now = time.time()
        record = self._memory_store.get(storage_key)
        if record is None or record[1] < now:
            self._memory_store[storage_key] = (payload_hash, now + self.config.ttl_seconds)
            return "claimed"

        existing_hash, expires_at = record
        if expires_at < now:
            self._memory_store[storage_key] = (payload_hash, now + self.config.ttl_seconds)
            return "claimed"
        if existing_hash == payload_hash:
            return "duplicate"
        return "conflict"


_service_cache: IdempotencyService | None = None


def get_idempotency_service(config: IdempotencyConfig) -> IdempotencyService:
    global _service_cache  # noqa: PLW0603 - cached singleton for reuse
    if _service_cache is None:
        _service_cache = IdempotencyService(config)
    return _service_cache
