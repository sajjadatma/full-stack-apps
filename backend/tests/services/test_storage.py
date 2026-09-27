from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from app.core.config import settings
from app.services.storage import (
    LocalStorageBackend,
    S3StorageBackend,
    StorageNamespace,
    StorageService,
    UploadValidationError,
    create_storage_backend,
)


def _png_bytes(size: int = 24) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"x" * (size - 8)


@pytest.mark.parametrize(
    ("content", "content_type", "suffix"),
    [
        (b"\xff\xd8\xff" + b"jpeg-data", "image/jpeg", ".jpg"),
        (_png_bytes(), "image/png", ".png"),
        (b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"webp-data", "image/webp", ".webp"),
    ],
)
def test_upload_accepts_supported_image_signatures(
    tmp_path: Path, content: bytes, content_type: str, suffix: str
) -> None:
    storage = StorageService(LocalStorageBackend(tmp_path), max_file_size_bytes=100)

    stored = storage.upload(
        content=content,
        content_type=content_type,
        namespace=StorageNamespace.PRODUCT_IMAGES,
    )

    assert stored.content_type == content_type
    assert stored.key.endswith(suffix)
    assert (tmp_path / stored.key).read_bytes() == content


def test_upload_creates_server_generated_namespaced_key_and_stores_bytes(
    tmp_path: Path,
) -> None:
    storage = StorageService(LocalStorageBackend(tmp_path), max_file_size_bytes=100)

    stored = storage.upload(
        content=_png_bytes(),
        content_type="image/png",
        namespace=StorageNamespace.PRODUCT_IMAGES,
    )

    assert stored.key.startswith("product-images/")
    assert Path(stored.key).name.endswith(".png")
    UUID(Path(stored.key).stem)
    assert stored.size_bytes == 24
    assert stored.content_type == "image/png"
    assert (tmp_path / stored.key).read_bytes() == _png_bytes()
    assert stored.access_url == f"/media/{stored.key}"


@pytest.mark.parametrize(
    ("content", "declared_type"),
    [
        (b"", "image/png"),
        (b"not an image", "image/png"),
        (_png_bytes(), "image/jpeg"),
        (b"\xff\xd8\xff" + b"x" * 16, "image/gif"),
    ],
)
def test_upload_rejects_empty_unsupported_or_mismatched_content(
    tmp_path: Path, content: bytes, declared_type: str
) -> None:
    storage = StorageService(LocalStorageBackend(tmp_path), max_file_size_bytes=100)

    with pytest.raises(UploadValidationError):
        storage.upload(
            content=content,
            content_type=declared_type,
            namespace=StorageNamespace.ROOM_PHOTOS,
        )


def test_upload_rejects_file_larger_than_configured_limit(tmp_path: Path) -> None:
    storage = StorageService(LocalStorageBackend(tmp_path), max_file_size_bytes=16)

    with pytest.raises(UploadValidationError, match="maximum"):
        storage.upload(
            content=_png_bytes(17),
            content_type="image/png",
            namespace=StorageNamespace.ROOM_PHOTOS,
        )


def test_local_backend_blocks_traversal_and_deletes_objects(tmp_path: Path) -> None:
    backend = LocalStorageBackend(tmp_path)
    storage = StorageService(backend, max_file_size_bytes=100)
    stored = storage.upload(
        content=_png_bytes(),
        content_type="image/png",
        namespace=StorageNamespace.ROOM_PHOTOS,
        private=True,
    )

    assert stored.access_url == f"/media/{stored.key}"
    for unsafe_key in ("../outside.png", ".", "/absolute.png", "a/../../b"):
        with pytest.raises(ValueError, match="unsafe"):
            backend.delete(unsafe_key)

    backend.delete(stored.key)
    assert not (tmp_path / stored.key).exists()


class FakeS3Client:
    def __init__(self) -> None:
        self.put_calls: list[dict[str, Any]] = []
        self.delete_calls: list[dict[str, Any]] = []
        self.presign_calls: list[dict[str, Any]] = []

    def put_object(self, **kwargs: Any) -> None:
        self.put_calls.append(kwargs)

    def delete_object(self, **kwargs: Any) -> None:
        self.delete_calls.append(kwargs)

    def generate_presigned_url(
        self, operation: str, *, Params: dict[str, Any], ExpiresIn: int
    ) -> str:
        self.presign_calls.append(
            {"operation": operation, "params": Params, "expires_in": ExpiresIn}
        )
        return "https://storage.example/signed"


def test_s3_backend_upload_delete_and_signed_private_access() -> None:
    client = FakeS3Client()
    backend = S3StorageBackend(
        bucket="tilevision-media", client=client, signed_url_ttl_seconds=240
    )

    backend.save("rooms/abc.png", _png_bytes(), "image/png")
    url = backend.access_url("rooms/abc.png", private=True)
    backend.delete("rooms/abc.png")

    assert client.put_calls == [
        {
            "Bucket": "tilevision-media",
            "Key": "rooms/abc.png",
            "Body": _png_bytes(),
            "ContentType": "image/png",
        }
    ]
    assert url == "https://storage.example/signed"
    assert client.presign_calls[0]["operation"] == "get_object"
    assert client.presign_calls[0]["expires_in"] == 240
    assert client.delete_calls == [
        {"Bucket": "tilevision-media", "Key": "rooms/abc.png"}
    ]


def test_s3_private_url_expiration_cannot_exceed_configured_ttl() -> None:
    client = FakeS3Client()
    backend = S3StorageBackend(
        bucket="tilevision-media", client=client, signed_url_ttl_seconds=300
    )

    backend.access_url("rooms/private.png", private=True, expires_in=3600)

    assert client.presign_calls[0]["expires_in"] == 300


def test_storage_configuration_selects_local_provider(tmp_path: Path) -> None:
    configured = settings.model_copy(
        update={"STORAGE_PROVIDER": "local", "STORAGE_LOCAL_ROOT": tmp_path}
    )

    backend = create_storage_backend(configured)

    assert isinstance(backend, LocalStorageBackend)
    assert backend.root == tmp_path.resolve()


def test_storage_configuration_selects_mocked_s3_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import boto3

    client = FakeS3Client()
    client_options: dict[str, Any] = {}

    def create_mock_client(*_args: Any, **kwargs: Any) -> FakeS3Client:
        client_options.update(kwargs)
        return client

    monkeypatch.setattr(boto3, "client", create_mock_client)
    configured = settings.model_copy(
        update={
            "STORAGE_PROVIDER": "s3",
            "STORAGE_S3_BUCKET": "tilevision-media",
            "STORAGE_S3_ENDPOINT_URL": "http://localhost:9000",
        }
    )

    backend = create_storage_backend(configured)

    assert isinstance(backend, S3StorageBackend)
    assert backend.bucket == "tilevision-media"
    assert client_options["endpoint_url"] == "http://localhost:9000"
    assert client_options["config"].s3["addressing_style"] == "path"
    assert backend.access_url("rooms/private.png", private=True)


def test_s3_backend_uses_public_object_url_without_signing() -> None:
    client = FakeS3Client()
    backend = S3StorageBackend(
        bucket="tilevision-media",
        client=client,
        public_base_url="https://cdn.example/media",
    )

    url = backend.access_url("product-images/abc.png", private=False)

    assert url == "https://cdn.example/media/product-images/abc.png"
    assert client.presign_calls == []
