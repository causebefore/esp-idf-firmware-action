#!/usr/bin/env python3
"""Validate a DeskSuite-compatible OTA package and prepare release assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


MAX_SAFE_JSON_INTEGER = 9_007_199_254_740_991
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
FIRMWARE_TARGET_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _positive_integer(value: object, field: str, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    if maximum is not None and value > maximum:
        raise ValueError(f"{field} exceeds the supported maximum")
    return value


def prepare_release(
    repository: str,
    firmware_path: Path,
    manifest_path: Path,
    output_dir: Path,
) -> dict[str, str]:
    if REPOSITORY_RE.fullmatch(repository) is None:
        raise ValueError("repository must use owner/repo format")
    if not firmware_path.is_file():
        raise ValueError(f"firmware file does not exist: {firmware_path}")
    if not manifest_path.is_file():
        raise ValueError(f"manifest file does not exist: {manifest_path}")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"manifest is not valid UTF-8 JSON: {manifest_path}") from exc
    if not isinstance(manifest, dict):
        raise ValueError("manifest root must be an object")

    firmware_target = manifest.get("firmware_target")
    if not isinstance(firmware_target, str) or FIRMWARE_TARGET_RE.fullmatch(firmware_target) is None:
        raise ValueError("firmware_target is invalid")
    product_id = _positive_integer(manifest.get("product_id"), "product_id")
    if manifest.get("protocol_version") != 2:
        raise ValueError("protocol_version must be 2")

    artifacts = manifest.get("artifacts")
    app = artifacts.get("app") if isinstance(artifacts, dict) else None
    if not isinstance(app, dict):
        raise ValueError("manifest artifacts.app must be an object")

    version = app.get("version")
    if not isinstance(version, str) or not version or len(version) > 64:
        raise ValueError("artifacts.app.version is invalid")
    ota_version = _positive_integer(
        app.get("ota_version"),
        "artifacts.app.ota_version",
        MAX_SAFE_JSON_INTEGER,
    )
    artifact_id = app.get("artifact_id")
    file_digest = app.get("file_sha256")
    if not isinstance(artifact_id, str) or SHA256_RE.fullmatch(artifact_id) is None:
        raise ValueError("artifacts.app.artifact_id must be a lowercase SHA-256 value")
    if not isinstance(file_digest, str) or SHA256_RE.fullmatch(file_digest) is None:
        raise ValueError("artifacts.app.file_sha256 must be a lowercase SHA-256 value")

    firmware_size = _positive_integer(app.get("size"), "artifacts.app.size")
    if firmware_path.stat().st_size != firmware_size:
        raise ValueError("firmware size does not match the manifest")
    if file_sha256(firmware_path) != file_digest:
        raise ValueError("firmware SHA-256 does not match the manifest")

    tag = f"{firmware_target}-v{ota_version}"
    firmware_name = f"{artifact_id}.bin"
    manifest_name = f"{firmware_target}.json"
    download_url = (
        f"https://github.com/{repository}/releases/download/{tag}/{firmware_name}"
    )
    app["download_url"] = download_url

    output_dir.mkdir(parents=True, exist_ok=False)
    firmware_asset = output_dir / firmware_name
    manifest_asset = output_dir / manifest_name
    shutil.copyfile(firmware_path, firmware_asset)
    manifest_asset.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "tag": tag,
        "release_title": f"{firmware_target} {version} (OTA {ota_version})",
        "download_url": download_url,
        "firmware_asset": str(firmware_asset.resolve()),
        "manifest_asset": str(manifest_asset.resolve()),
        "product_id": str(product_id),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--firmware", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        package = prepare_release(
            args.repository,
            args.firmware,
            args.manifest,
            args.output_dir,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(package, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
