from __future__ import annotations

import pytest

from agent_core.artifacts.distribution import (
    ArtifactDistributionRouter,
    LocalArtifactBackend,
    S3ArtifactBackend,
)


@pytest.mark.asyncio
async def test_artifact_distribution_multi_backend():
    """Kiểm thử Multi-Backend Artifact Distribution."""
    router = ArtifactDistributionRouter(default_backend=LocalArtifactBackend())
    s3_backend = S3ArtifactBackend(bucket="my-company-artifacts")
    router.register_backend("s3", s3_backend)

    data = b"id,name,score\n1,Alpha,95\n2,Beta,88\n"

    # 1. Lưu trữ qua local backend
    uri_local = await router.store_artifact("art_001", data, preferred_scheme="local")
    assert uri_local.startswith("local://")
    loaded_local = await router.load_artifact(uri_local)
    assert loaded_local == data

    # 2. Lưu trữ qua S3 backend
    uri_s3 = await router.store_artifact("art_002", data, preferred_scheme="s3")
    assert uri_s3.startswith("s3://my-company-artifacts/art_002")
    loaded_s3 = await router.load_artifact(uri_s3)
    assert loaded_s3 == data
