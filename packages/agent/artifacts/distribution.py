from __future__ import annotations

from typing import Protocol

__all__ = [
    "ArtifactDistributionRouter",
    "ArtifactStorageBackend",
    "FakeS3ArtifactBackend",
    "LocalArtifactBackend",
]


class ArtifactStorageBackend(Protocol):
    async def upload(self, key: str, data: bytes, media_type: str) -> str: ...
    async def download(self, key: str) -> bytes: ...
    async def exists(self, key: str) -> bool: ...


class LocalArtifactBackend:
    """In-memory / Local storage backend cho Artifacts."""

    def __init__(self, prefix: str = "local://") -> None:
        self._prefix = prefix
        self._store: dict[str, tuple[bytes, str]] = {}

    async def upload(self, key: str, data: bytes, media_type: str = "text/plain") -> str:
        self._store[key] = (data, media_type)
        return f"{self._prefix}{key}"

    async def download(self, key: str) -> bytes:
        if key not in self._store:
            raise FileNotFoundError(f"Artifact key '{key}' not found")
        return self._store[key][0]

    async def exists(self, key: str) -> bool:
        return key in self._store


class FakeS3ArtifactBackend:
    """Test double mô phỏng S3 (in-memory, KHÔNG gọi SDK S3/boto3 nào) — dùng
    để test `ArtifactDistributionRouter` với nhiều backend/scheme (vd
    `s3://bucket/key`) mà không cần dependency S3 thật. Tên cũ
    `S3ArtifactBackend` (trước P1.3) gây hiểu nhầm là backend S3 production
    thật dù nhận `bucket`/`region` như thể vậy — đây thuần là fake, nếu cần
    S3 thật hãy implement 1 class riêng dùng `boto3`/`aioboto3`."""

    def __init__(self, bucket: str = "cosa-artifacts-prod", region: str = "ap-southeast-1") -> None:
        self.bucket = bucket
        self.region = region
        self._remote_store: dict[str, tuple[bytes, str]] = {}

    async def upload(self, key: str, data: bytes, media_type: str = "text/plain") -> str:
        self._remote_store[key] = (data, media_type)
        return f"s3://{self.bucket}/{key}"

    async def download(self, key: str) -> bytes:
        clean_key = key[len(self.bucket) + 1 :] if key.startswith(f"{self.bucket}/") else key
        if clean_key not in self._remote_store:
            raise FileNotFoundError(f"S3 object '{clean_key}' not found in bucket '{self.bucket}'")
        return self._remote_store[clean_key][0]

    async def exists(self, key: str) -> bool:
        return key in self._remote_store


class ArtifactDistributionRouter:
    """Router phân phối lưu trữ Artifact đa vùng / đa cloud."""

    def __init__(self, default_backend: ArtifactStorageBackend | None = None) -> None:
        self._default = default_backend or LocalArtifactBackend()
        self._backends: dict[str, ArtifactStorageBackend] = {"local": self._default}

    def register_backend(self, scheme: str, backend: ArtifactStorageBackend) -> None:
        self._backends[scheme] = backend

    async def store_artifact(
        self,
        artifact_id: str,
        data: bytes,
        media_type: str = "text/plain",
        preferred_scheme: str = "local",
    ) -> str:
        backend = self._backends.get(preferred_scheme, self._default)
        return await backend.upload(artifact_id, data, media_type)

    async def load_artifact(self, uri: str) -> bytes:
        scheme = uri.split("://", maxsplit=1)[0] if "://" in uri else "local"
        key = uri.split("://", 1)[1] if "://" in uri else uri
        backend = self._backends.get(scheme, self._default)
        return await backend.download(key)
