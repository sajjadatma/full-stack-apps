from __future__ import annotations


class ImageMetadataError(ValueError):
    """Raised when supported image bytes do not contain readable dimensions."""


def image_dimensions(content: bytes, content_type: str) -> tuple[int, int]:
    """Read pixel dimensions from JPEG, PNG, and WebP image headers."""
    if content_type == "image/png":
        if (
            len(content) < 24
            or not content.startswith(b"\x89PNG\r\n\x1a\n")
            or content[12:16] != b"IHDR"
        ):
            raise ImageMetadataError("PNG image has an invalid or incomplete header")
        width = int.from_bytes(content[16:20], "big")
        height = int.from_bytes(content[20:24], "big")
    elif content_type == "image/jpeg":
        width, height = _jpeg_dimensions(content)
    elif content_type == "image/webp":
        width, height = _webp_dimensions(content)
    else:
        raise ImageMetadataError("Only JPEG, PNG, and WebP images are accepted")

    if width <= 0 or height <= 0:
        raise ImageMetadataError("Image dimensions must be greater than zero")
    return width, height


def _jpeg_dimensions(content: bytes) -> tuple[int, int]:
    if not content.startswith(b"\xff\xd8"):
        raise ImageMetadataError("JPEG image has an invalid header")

    start_of_frame_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    offset = 2
    while offset < len(content):
        if content[offset] != 0xFF:
            offset += 1
            continue
        while offset < len(content) and content[offset] == 0xFF:
            offset += 1
        if offset >= len(content):
            break
        marker = content[offset]
        offset += 1
        if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7 or marker == 0x01:
            continue
        if offset + 2 > len(content):
            break
        segment_length = int.from_bytes(content[offset : offset + 2], "big")
        if segment_length < 2 or offset + segment_length > len(content):
            break
        if marker in start_of_frame_markers:
            if segment_length < 7:
                break
            height = int.from_bytes(content[offset + 3 : offset + 5], "big")
            width = int.from_bytes(content[offset + 5 : offset + 7], "big")
            return width, height
        offset += segment_length
    raise ImageMetadataError("JPEG image has no readable dimensions")


def _webp_dimensions(content: bytes) -> tuple[int, int]:
    if len(content) < 30 or not content.startswith(b"RIFF") or content[8:12] != b"WEBP":
        raise ImageMetadataError("WebP image has an invalid or incomplete header")

    chunk_type = content[12:16]
    if chunk_type == b"VP8X":
        width = int.from_bytes(content[24:27], "little") + 1
        height = int.from_bytes(content[27:30], "little") + 1
        return width, height
    if chunk_type == b"VP8 " and content[23:26] == b"\x9d\x01\x2a":
        width = int.from_bytes(content[26:28], "little") & 0x3FFF
        height = int.from_bytes(content[28:30], "little") & 0x3FFF
        return width, height
    if chunk_type == b"VP8L" and content[20] == 0x2F:
        bits = int.from_bytes(content[21:25], "little")
        width = (bits & 0x3FFF) + 1
        height = ((bits >> 14) & 0x3FFF) + 1
        return width, height
    raise ImageMetadataError("WebP image has no readable dimensions")
