from __future__ import annotations

import time
import pytest

from spoilerless.app.domain.share import ShareTokenCreate, ShareTokenRecord
from spoilerless.app.repository.share import (
    InMemoryShareRepository,
    _hash_token,
)


@pytest.mark.asyncio
async def test_share_repository_hash_storage_and_retrieval() -> None:
    repo = InMemoryShareRepository()
    creator = "user:creator123"

    raw_token, record = await repo.create(
        created_by=creator,
        series_id="series_dexter",
        visible_until_order=3,
        ttl_seconds=3600,
    )

    # Raw token is returned, but store has hash
    assert raw_token != record.token_hash
    assert record.token_hash == _hash_token(raw_token)
    assert record.series_id == "series_dexter"
    assert record.visible_until_order == 3
    assert record.created_by == creator
    assert record.revoked_at is None

    # Fetch by token_hash
    fetched = await repo.get_by_token_hash(record.token_hash)
    assert fetched is not None
    assert fetched.id == record.id

    # Fetch by raw_token
    fetched_raw = await repo.get_by_raw_token(raw_token)
    assert fetched_raw is not None
    assert fetched_raw.id == record.id


@pytest.mark.asyncio
async def test_share_repository_expiry_and_revocation() -> None:
    repo = InMemoryShareRepository()
    creator = "user:creator123"

    # Expired token
    raw_exp, rec_exp = await repo.create(
        created_by=creator,
        series_id="series_dexter",
        visible_until_order=1,
        ttl_seconds=-10,  # Already expired
    )
    assert rec_exp.is_expired
    assert await repo.get_by_token_hash(rec_exp.token_hash) is None
    assert await repo.get_by_raw_token(raw_exp) is None

    # Revoked token
    raw_rev, rec_rev = await repo.create(
        created_by=creator,
        series_id="series_dexter",
        visible_until_order=2,
        ttl_seconds=3600,
    )
    assert not rec_rev.is_revoked
    revoked_ok = await repo.revoke(rec_rev.token_hash)
    assert revoked_ok is True
    assert await repo.get_by_token_hash(rec_rev.token_hash) is None

    # Revoking non-existent / already revoked
    assert await repo.revoke("nonexistent") is False
    assert await repo.revoke(rec_rev.token_hash) is False


@pytest.mark.asyncio
async def test_share_repository_list_active_and_sweep() -> None:
    repo = InMemoryShareRepository()
    creator1 = "user:creator1"
    creator2 = "user:creator2"

    raw1, rec1 = await repo.create(creator1, "series_dexter", 1, ttl_seconds=3600)
    raw2, rec2 = await repo.create(creator1, "series_dexter", 2, ttl_seconds=3600)
    raw3, rec3 = await repo.create(creator2, "series_dexter", 3, ttl_seconds=3600)

    # list_active creator scoped
    c1_tokens = await repo.list_active(creator1)
    assert len(c1_tokens) == 2
    assert {t.id for t in c1_tokens} == {rec1.id, rec2.id}

    c2_tokens = await repo.list_active(creator2)
    assert len(c2_tokens) == 1
    assert c2_tokens[0].id == rec3.id

    # Revoke one of creator1's tokens
    await repo.revoke(rec1.token_hash)
    c1_active = await repo.list_active(creator1)
    assert len(c1_active) == 1
    assert c1_active[0].id == rec2.id

    # Sweep
    swept = await repo.sweep_expired()
    assert swept == 1  # rec1 was revoked
