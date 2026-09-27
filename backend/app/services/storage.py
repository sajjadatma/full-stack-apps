from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Protocol
from urllib.parse import quote
from uuid import uuid4

from app.core.config import Settings


class StorageNamespace(StrEnum):
    PRODUCT_IMAGES = "product-images"
    ROOM_PHOTOS = "rooms"
    GENERATION_RESULTS = "generation-results"


class UploadValidationError(ValueError):
    """Raised when uploaded bytes are not an allowed image."""


class StorageBackend(Protocol):
    def save(self, key: str, content: bytes, content_type: str) -> None: ...

    def delete(self, key: str) -> None: ...

    def access_url(
        self, key: str, *, private: bool, expires_in: int | None = None
    ) -> str: ...

    def stream(self, key: str) -> Iterator[bytes]: ...


@dataclass(frozen=True)
class StoredObject:
    key: str
    content_type: str
    size_bytes: int
    access_url: str
    private: bool


_IMAGE_SIGNATURES = {
    "image/jpeg": (lambda content: content.startswith(b"\xff\xd8\xff"), ".jpg"),
    "image/png": (lambda content: content.startswith(b"\x89PNG\r\n\x1a\n"), ".png"),
    "image/webp": (
        lambda content: (
            len(content) >= 12
            and content.startswith(b"RIFF")
            and content[8:12] == b"WEBP"
        ),
        ".webp",
    ),
}


def _safe_key(key: str) -> PurePosixPath:
    if not key or "\\" in key or "\x00" in key:
        raise ValueError("unsafe storage key")
    path = PurePosixPath(key)
    if (
        not path.parts
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError("unsafe storage key")
    return path


class StorageService:
    def __init__(self, backend: StorageBackend, *, max_file_size_bytes: int) -> None:
        if max_file_size_bytes <= 0:
            raise ValueError("max_file_size_bytes must be greater than zero")
        self.backend = backend
        self.max_file_size_bytes = max_file_size_bytes

    def upload(
        self,
        *,
        content: bytes,
        content_type: str,
        namespace: StorageNamespace,
        private: bool = False,
    ) -> StoredObject:
        if not content:
            raise UploadValidationError("Image file cannot be empty")
        if len(content) > self.max_file_size_bytes:
            raise UploadValidationError(
                f"Image exceeds the maximum size of {self.max_file_size_bytes} bytes"
            )
        signature = _IMAGE_SIGNATURES.get(content_type)
        if signature is None or not signature[0](content):
            raise UploadValidationError(
                "Only valid JPEG, PNG, and WebP images are accepted"
            )

        key = f"{namespace.value}/{uuid4().hex}{signature[1]}"
        _safe_key(key)
        self.backend.save(key, content, content_type)
        return StoredObject(
            key=key,
            content_type=content_type,
            size_bytes=len(content),
            access_url=self.backend.access_url(key, private=private),
            private=private,
        )

    def delete(self, key: str) -> None:
        _safe_key(key)
        self.backend.delete(key)

    def access_url(
        self,
        key: str,
        *,
        private: bool = False,
        expires_in: int | None = None,
        local_url: str | None = None,
    ) -> str:
        _safe_key(key)
        if isinstance(self.backend, LocalStorageBackend) and local_url is not None:
            return local_url
        return self.backend.access_url(key, private=private, expires_in=expires_in)

    def stream(self, key: str) -> Iterator[bytes]:
        _safe_key(key)
        return self.backend.stream(key)


class LocalStorageBackend:
    def __init__(self, root: Path, *, url_prefix: str = "/media") -> None:
        self.root = root.expanduser().resolve()
        self.url_prefix = url_prefix.rstrip("/")

    def _path_for_key(self, key: str) -> Path:
        relative = _safe_key(key)
        path = (self.root / Path(*relative.parts)).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("unsafe storage key")
        return path

    def save(self, key: str, content: bytes, content_type: str) -> None:
        del (
            content_type
        )  # The local filesystem stores bytes; metadata is returned by the service.
        path = self._path_for_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def delete(self, key: str) -> None:
        self._path_for_key(key).unlink(missing_ok=True)

    def access_url(
        self, key: str, *, private: bool, expires_in: int | None = None
    ) -> str:
        del private, expires_in
        relative = _safe_key(key)
        encoded_key = quote(relative.as_posix(), safe="/")
        return f"{self.url_prefix}/{encoded_key}"

    def stream(self, key: str) -> Iterator[bytes]:
        path = self._path_for_key(key)
        if not path.is_file():
            raise FileNotFoundError(key)

        def chunks() -> Iterator[bytes]:
            with path.open("rb") as content_file:
                while chunk := content_file.read(64 * 1024):
                    yield chunk

        return chunks()


class S3StorageBackend:
    def __init__(
        self,
        *,
        bucket: str,
        client: Any,
        signed_url_ttl_seconds: int = 300,
        public_base_url: str | None = None,
    ) -> None:
        if signed_url_ttl_seconds <= 0:
            raise ValueError("signed_url_ttl_seconds must be greater than zero")
        self.bucket = bucket
        self.client = client
        self.signed_url_ttl_seconds = signed_url_ttl_seconds
        self.public_base_url = public_base_url.rstrip("/") if public_base_url else None

    def save(self, key: str, content: bytes, content_type: str) -> None:
        _safe_key(key)
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=content, ContentType=content_type
        )

    def delete(self, key: str) -> None:
        _safe_key(key)
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def access_url(
        self, key: str, *, private: bool, expires_in: int | None = None
    ) -> str:
        relative = _safe_key(key).as_posix()
        encoded_key = quote(relative, safe="/")
        if not private and self.public_base_url:
            return f"{self.public_base_url}/{encoded_key}"
        requested_ttl = (
            self.signed_url_ttl_seconds if expires_in is None else expires_in
        )
        ttl = min(requested_ttl, self.signed_url_ttl_seconds)
        if ttl <= 0:
            raise ValueError("signed URL expiration must be greater than zero")
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": relative},
            ExpiresIn=ttl,
        )

    def stream(self, key: str) -> Iterator[bytes]:
        _safe_key(key)
        body = self.client.get_object(Bucket=self.bucket, Key=key)["Body"]

        def chunks() -> Iterator[bytes]:
            try:
                yield from body.iter_chunks(chunk_size=64 * 1024)
            finally:
                body.close()

        return chunks()


def create_storage_backend(settings: Settings) -> StorageBackend:
    provider = settings.STORAGE_PROVIDER
    if provider == "local":
        return LocalStorageBackend(
            settings.STORAGE_LOCAL_ROOT,
            url_prefix=settings.STORAGE_LOCAL_URL_PREFIX,
        )
    if provider == "s3":
        if settings.STORAGE_S3_BUCKET is None:
            raise ValueError("STORAGE_S3_BUCKET is required when STORAGE_PROVIDER=s3")
        import boto3
        from botocore.config import Config

        client_options: dict[str, object | None] = {
            "endpoint_url": settings.STORAGE_S3_ENDPOINT_URL,
            "region_name": settings.STORAGE_S3_REGION,
            "aws_access_key_id": settings.STORAGE_S3_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.STORAGE_S3_SECRET_ACCESS_KEY,
        }
        if settings.STORAGE_S3_ENDPOINT_URL:
            client_options["config"] = Config(s3={"addressing_style": "path"})
        client = boto3.client(
            "s3", **{key: value for key, value in client_options.items() if value}
        )
        return S3StorageBackend(
            bucket=settings.STORAGE_S3_BUCKET,
            client=client,
            signed_url_ttl_seconds=settings.STORAGE_S3_SIGNED_URL_TTL_SECONDS,
            public_base_url=settings.STORAGE_S3_PUBLIC_BASE_URL,
        )
    raise ValueError(f"Unsupported storage provider: {provider}")


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    from app.core.config import settings

    return StorageService(
        create_storage_backend(settings),
        max_file_size_bytes=settings.STORAGE_MAX_FILE_SIZE_BYTES,
    )
