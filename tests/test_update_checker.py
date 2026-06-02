from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _response(json_data=None, status=200, content=b""):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_data or {}
    r.content = content
    r.iter_bytes.return_value = [content]
    r.raise_for_status = MagicMock()
    return r


def _release(tag="v0.2.0", assets=None):
    return {
        "tag_name": tag,
        "html_url": "https://github.com/yorjungai-cmd/FolderRenamer/releases/tag/v0.2.0",
        "body": "Release notes",
        "assets": assets or [
            {
                "name": "FolderFileRenamer-v0.2.0.exe",
                "browser_download_url": "https://example.test/app.exe",
                "size": 1234,
            },
            {
                "name": "FolderFileRenamer-v0.2.0.exe.sha256",
                "browser_download_url": "https://example.test/app.exe.sha256",
                "size": 80,
            },
        ],
    }


def test_version_tag_is_newer_than_current():
    from core.update_checker import is_newer_version

    assert is_newer_version("v0.2.0", "0.1.0") is True


def test_same_version_is_not_newer():
    from core.update_checker import is_newer_version

    assert is_newer_version("0.1.0", "0.1.0") is False


def test_invalid_version_tag_is_not_newer():
    from core.update_checker import is_newer_version

    assert is_newer_version("latest", "0.1.0") is False


def test_check_for_update_finds_matching_exe_asset(mocker):
    from core.update_checker import check_for_update

    mocker.patch("httpx.get", return_value=_response(_release()))

    info = check_for_update("0.1.0", "yorjungai-cmd", "FolderRenamer")

    assert info.update_available is True
    assert info.latest_version == "0.2.0"
    assert info.asset_name == "FolderFileRenamer-v0.2.0.exe"
    assert info.asset_url == "https://example.test/app.exe"
    assert info.checksum_url == "https://example.test/app.exe.sha256"


def test_check_for_update_rejects_release_without_matching_exe(mocker):
    from core.update_checker import UpdateError, check_for_update

    mocker.patch(
        "httpx.get",
        return_value=_response(_release(assets=[{"name": "source.zip", "browser_download_url": "x", "size": 1}])),
    )

    with pytest.raises(UpdateError, match="No Windows EXE asset"):
        check_for_update("0.1.0", "yorjungai-cmd", "FolderRenamer")


def test_check_for_update_handles_no_github_release(mocker):
    from core.update_checker import check_for_update

    mocker.patch("httpx.get", return_value=_response({"message": "Not Found"}, status=404))

    info = check_for_update("0.1.0", "yorjungai-cmd", "FolderRenamer")

    assert info.update_available is False
    assert info.latest_version == "0.1.0"
    assert info.message == "No GitHub release is available yet."


def test_download_update_accepts_matching_sha256(tmp_path, mocker):
    from core.update_checker import UpdateInfo, download_update

    payload = b"new exe bytes"
    digest = "859246c23ce49267759d2993722cf5732aa5df30ab8c01eb4b965aafad4669ed"
    info = UpdateInfo(
        current_version="0.1.0",
        latest_version="0.2.0",
        update_available=True,
        release_url="https://example.test/release",
        asset_url="https://example.test/app.exe",
        asset_name="FolderFileRenamer-v0.2.0.exe",
        asset_size=123,
        notes="",
        checksum_url="https://example.test/app.exe.sha256",
    )
    mocker.patch("httpx.stream", return_value=_StreamResponse(payload))
    mocker.patch("httpx.get", return_value=_response(content=f"{digest}  {info.asset_name}\n".encode()))

    downloaded = download_update(info, tmp_path)

    assert downloaded == tmp_path / "FolderFileRenamer-v0.2.0.exe"
    assert downloaded.read_bytes() == payload


def test_download_update_rejects_mismatched_sha256(tmp_path, mocker):
    from core.update_checker import UpdateError, UpdateInfo, download_update

    info = UpdateInfo(
        current_version="0.1.0",
        latest_version="0.2.0",
        update_available=True,
        release_url="https://example.test/release",
        asset_url="https://example.test/app.exe",
        asset_name="FolderFileRenamer-v0.2.0.exe",
        asset_size=123,
        notes="",
        checksum_url="https://example.test/app.exe.sha256",
    )
    mocker.patch("httpx.stream", return_value=_StreamResponse(b"new exe bytes"))
    mocker.patch("httpx.get", return_value=_response(content=b"0" * 64))

    with pytest.raises(UpdateError, match="Checksum verification failed"):
        download_update(info, tmp_path)

    assert not (tmp_path / "FolderFileRenamer-v0.2.0.exe").exists()


class _StreamResponse:
    def __init__(self, payload):
        self.payload = payload
        self.headers = {"content-length": str(len(payload))}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    def iter_bytes(self):
        yield self.payload
