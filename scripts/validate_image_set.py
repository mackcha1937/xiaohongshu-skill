#!/usr/bin/env python3
"""Validate a numbered Xiaohongshu image set without third-party packages."""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path


SUPPORTED = {".png", ".jpg", ".jpeg"}


def png_size(data: bytes) -> tuple[int, int]:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("invalid PNG")
    return struct.unpack(">II", data[16:24])


def jpeg_size(data: bytes) -> tuple[int, int]:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        raise ValueError("invalid JPEG")
    offset = 2
    sof_markers = {
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
    while offset + 4 <= len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9}:
            continue
        if offset + 2 > len(data):
            break
        length = struct.unpack(">H", data[offset : offset + 2])[0]
        if length < 2 or offset + length > len(data):
            break
        if marker in sof_markers and length >= 7:
            height, width = struct.unpack(">HH", data[offset + 3 : offset + 7])
            return width, height
        offset += length
    raise ValueError("JPEG dimensions not found")


def image_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if path.suffix.lower() == ".png":
        return png_size(data)
    return jpeg_size(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--min-count", type=int, default=4)
    args = parser.parse_args()

    errors: list[str] = []
    if not args.folder.is_dir():
        print(f"ERROR: folder not found: {args.folder}")
        return 1

    files = sorted(
        path
        for path in args.folder.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED
    )
    if len(files) < args.min_count:
        errors.append(f"need at least {args.min_count} images, found {len(files)}")

    if args.keyword is not None and len(args.keyword) > 4:
        errors.append(f"keyword must be <= 4 characters: {args.keyword!r}")

    if files and not files[0].name.startswith("01"):
        errors.append(f"first image must start with 01: {files[0].name}")

    for index, path in enumerate(files, start=1):
        try:
            width, height = image_size(path)
        except (OSError, ValueError) as exc:
            errors.append(f"{path.name}: {exc}")
            continue

        expected_prefix = f"{index:02d}"
        if not path.name.startswith(expected_prefix):
            errors.append(
                f"{path.name}: expected filename prefix {expected_prefix}"
            )
        if width < 720 or height < 960:
            errors.append(f"{path.name}: resolution too small ({width}x{height})")
        if width * 4 != height * 3:
            errors.append(f"{path.name}: ratio is not 3:4 ({width}x{height})")
        print(f"OK {path.name}: {width}x{height}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"PASS: {len(files)} images ready for Xiaohongshu")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
