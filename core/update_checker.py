import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx


GITHUB_API_VERSION = "2022-11-28"
EXE_NAME_TEMPLATE = "FolderFileRenamer-v{version}.exe"


class UpdateError(Exception):
    pass


@dataclass
class UpdateInfo:
    current_version: str
    latest_version: str
    update_available: bool
    release_url: str
    asset_url: str
    asset_name: str
    asset_size: int
    notes: str
    checksum_url: str = ""
    message: str = ""


def _parse_version(version: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", version.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def _normalize_version(version: str) -> str:
    parsed = _parse_version(version)
    if parsed is None:
        raise UpdateError(f"Invalid version tag: {version}")
    return ".".join(str(part) for part in parsed)


def is_newer_version(candidate: str, current: str) -> bool:
    candidate_version = _parse_version(candidate)
    current_version = _parse_version(current)
    if candidate_version is None or current_version is None:
        return False
    return candidate_version > current_version


def get_latest_release(owner: str, repo: str, timeout_s: int = 10) -> dict:
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    response = httpx.get(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": "FolderFileRenamer-Updater",
        },
        timeout=timeout_s,
    )
    if response.status_code == 404:
        return {}
    response.raise_for_status()
    return response.json()


def _find_asset(release: dict, name: str) -> dict | None:
    for asset in release.get("assets", []):
        if asset.get("name") == name:
            return asset
    return None


def check_for_update(current_version: str, owner: str, repo: str, timeout_s: int = 10) -> UpdateInfo:
    release = get_latest_release(owner, repo, timeout_s=timeout_s)
    if not release:
        return UpdateInfo(
            current_version=current_version,
            latest_version=current_version,
            update_available=False,
            release_url="",
            asset_url="",
            asset_name="",
            asset_size=0,
            notes="",
            message="No GitHub release is available yet.",
        )

    latest_version = _normalize_version(release.get("tag_name", ""))
    update_available = is_newer_version(latest_version, current_version)
    asset_name = EXE_NAME_TEMPLATE.format(version=latest_version)
    asset = _find_asset(release, asset_name)
    if update_available and not asset:
        raise UpdateError(f"No Windows EXE asset named {asset_name} was found in the latest release.")

    checksum = _find_asset(release, f"{asset_name}.sha256")
    return UpdateInfo(
        current_version=current_version,
        latest_version=latest_version,
        update_available=update_available,
        release_url=release.get("html_url", ""),
        asset_url=asset.get("browser_download_url", "") if asset else "",
        asset_name=asset.get("name", "") if asset else "",
        asset_size=int(asset.get("size", 0)) if asset else 0,
        notes=release.get("body") or "",
        checksum_url=checksum.get("browser_download_url", "") if checksum else "",
        message="" if update_available else "You are already running the latest version.",
    )


def _expected_sha256(checksum_text: str) -> str:
    match = re.search(r"\b[a-fA-F0-9]{64}\b", checksum_text)
    if not match:
        raise UpdateError("Checksum file does not contain a valid SHA256 digest.")
    return match.group(0).lower()


def _download_checksum(url: str, timeout_s: int) -> str:
    response = httpx.get(url, timeout=timeout_s)
    response.raise_for_status()
    return _expected_sha256(response.content.decode("utf-8", errors="replace"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_update(
    update_info: UpdateInfo,
    target_dir: str | Path,
    progress_callback: Callable[[int, int], None] | None = None,
    timeout_s: int = 60,
) -> Path:
    if not update_info.update_available or not update_info.asset_url or not update_info.asset_name:
        raise UpdateError("No update asset is available to download.")
    if not update_info.checksum_url:
        raise UpdateError("No SHA256 checksum asset is available for this update.")

    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    output = target / update_info.asset_name
    temp = output.with_suffix(output.suffix + ".download")
    bytes_read = 0

    try:
        with httpx.stream("GET", update_info.asset_url, timeout=timeout_s, follow_redirects=True) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length") or update_info.asset_size or 0)
            with temp.open("wb") as f:
                for chunk in response.iter_bytes():
                    if not chunk:
                        continue
                    f.write(chunk)
                    bytes_read += len(chunk)
                    if progress_callback:
                        progress_callback(bytes_read, total)
        temp.replace(output)

        expected = _download_checksum(update_info.checksum_url, timeout_s)
        actual = _sha256_file(output)
        if actual != expected:
            output.unlink(missing_ok=True)
            raise UpdateError("Checksum verification failed.")
        return output
    except UpdateError:
        temp.unlink(missing_ok=True)
        raise
    except Exception:
        temp.unlink(missing_ok=True)
        raise
