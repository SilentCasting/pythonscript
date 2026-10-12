"""Format-aware ways to make a file's bytes unique without changing what it shows.

Each injector takes the original file bytes plus a random payload and returns
new bytes. Where the format allows it, the payload goes into a metadata block
that image viewers ignore (a PNG text chunk, a JPEG comment, a GIF comment
extension), so the result is still a fully valid file. Every other format gets
the payload appended after the end of the image data, which decoders skip.
"""

from __future__ import annotations

import struct
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# Keyword of the PNG tEXt chunk we add, so the chunk is easy to recognise.
PNG_KEYWORD = b"ChangeImageHash"

# Human-readable names for the methods, shown in the CLI and the app.
METHOD_PNG = "PNG text chunk"
METHOD_JPEG = "JPEG comment"
METHOD_GIF = "GIF comment"
METHOD_APPEND = "Appended bytes"


class FormatError(ValueError):
    """Raised when a file looks like a known format but its structure is broken."""


def detect_format(data: bytes) -> str:
    """Return a short format name based on the file's magic bytes."""
    if data.startswith(PNG_SIGNATURE):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:2] == b"BM":
        return "bmp"
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"
    return "other"


def _inject_png(data: bytes, payload: bytes) -> bytes:
    """Insert a tEXt chunk right before IEND, the last chunk of every PNG."""
    pos = len(PNG_SIGNATURE)
    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        chunk_type = data[pos + 4 : pos + 8]
        if chunk_type == b"IEND":
            body = PNG_KEYWORD + b"\x00" + payload
            crc = zlib.crc32(b"tEXt" + body)
            chunk = struct.pack(">I", len(body)) + b"tEXt" + body + struct.pack(">I", crc)
            return data[:pos] + chunk + data[pos:]
        # Each chunk is: 4 bytes length + 4 bytes type + data + 4 bytes CRC.
        pos += 12 + length
    raise FormatError("PNG file has no IEND chunk")


def _inject_jpeg(data: bytes, payload: bytes) -> bytes:
    """Insert a COM (comment) segment after the leading APPn segments.

    JFIF and EXIF readers expect their APP0/APP1 segment to come straight
    after the SOI marker, so the comment goes after those instead of before.
    """
    pos = 2  # skip the SOI marker (FF D8)
    while pos + 4 <= len(data) and data[pos] == 0xFF and 0xE0 <= data[pos + 1] <= 0xEF:
        (length,) = struct.unpack(">H", data[pos + 2 : pos + 4])
        pos += 2 + length
    if pos > len(data):
        raise FormatError("JPEG segment runs past the end of the file")
    # The segment length field counts itself (2 bytes) but not the marker.
    segment = b"\xff\xfe" + struct.pack(">H", len(payload) + 2) + payload
    return data[:pos] + segment + data[pos:]


def _can_comment_gif(data: bytes, payload: bytes) -> bool:
    """The trailer (0x3B) must be the last byte and the payload fit one sub-block."""
    return data.endswith(b"\x3b") and len(payload) <= 255


def _inject_gif(data: bytes, payload: bytes) -> bytes:
    """Insert a comment extension right before the GIF trailer byte (0x3B).

    Comment extensions were added in GIF89a, which is a strict superset of
    GIF87a, so older files simply get their version bumped to 89a.
    """
    # 0x21 0xFE starts a comment extension; a zero-length sub-block ends it.
    block = b"\x21\xfe" + bytes([len(payload)]) + payload + b"\x00"
    return b"GIF89a" + data[6:-1] + block + b"\x3b"


def _append(data: bytes, payload: bytes) -> bytes:
    """Append the payload after the image data; decoders stop before it."""
    return data + payload


def inject(data: bytes, payload: bytes) -> tuple[bytes, str]:
    """Return ``(new_data, method)`` with ``payload`` hidden inside ``data``.

    ``payload`` must be plain ASCII so it is valid inside PNG text chunks.
    """
    kind = detect_format(data)
    if kind == "png":
        return _inject_png(data, payload), METHOD_PNG
    if kind == "jpeg":
        return _inject_jpeg(data, payload), METHOD_JPEG
    if kind == "gif" and _can_comment_gif(data, payload):
        return _inject_gif(data, payload), METHOD_GIF
    return _append(data, payload), METHOD_APPEND
