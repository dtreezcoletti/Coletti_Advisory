from __future__ import annotations

import io
import re
import stat
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


MAX_SINGLE_UPLOAD_BYTES = 200 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 500
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 500 * 1024 * 1024
MAX_ARCHIVE_MEMBER_BYTES = 100 * 1024 * 1024
MAX_COMPRESSION_RATIO = 250.0
MAX_ARCHIVE_DEPTH = 2

BLOCKED_ARCHIVE_SUFFIXES = {
    ".exe", ".dll", ".bat", ".cmd", ".com", ".scr", ".msi", ".ps1", ".vbs", ".jar",
    ".apk", ".app", ".dmg", ".iso", ".pkg", ".deb", ".rpm",
}

_GOOGLE_FILE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,}$")


class IngestionSafetyError(ValueError):
    pass


@dataclass(frozen=True)
class ArchiveItem:
    path: str
    filename: str
    data: bytes
    nested: tuple["ArchiveItem", ...] = ()


@dataclass(frozen=True)
class ArchiveInspection:
    items: tuple[ArchiveItem, ...]
    file_count: int
    total_uncompressed_bytes: int


def _normalized_member_path(name: str) -> PurePosixPath:
    normalized = name.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise IngestionSafetyError(f"Unsafe archive path rejected: {name!r}")
    return path


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def _check_member(info: zipfile.ZipInfo) -> PurePosixPath:
    path = _normalized_member_path(info.filename)
    if info.flag_bits & 0x1:
        raise IngestionSafetyError(f"Encrypted/password-protected archive member is not supported: {path}")
    if _is_symlink(info):
        raise IngestionSafetyError(f"Archive symlink rejected: {path}")
    if path.suffix.lower() in BLOCKED_ARCHIVE_SUFFIXES:
        raise IngestionSafetyError(f"Executable or package file rejected from archive: {path}")
    if info.file_size > MAX_ARCHIVE_MEMBER_BYTES:
        raise IngestionSafetyError(f"Archive member exceeds the per-file extraction limit: {path}")
    compressed = max(1, int(info.compress_size))
    ratio = float(info.file_size) / float(compressed)
    if info.file_size > 1024 * 1024 and ratio > MAX_COMPRESSION_RATIO:
        raise IngestionSafetyError(f"Suspicious compression ratio rejected for archive member: {path}")
    return path


def inspect_zip(data: bytes, *, depth: int = 0) -> ArchiveInspection:
    if not data:
        raise IngestionSafetyError("Cannot inspect an empty archive")
    if len(data) > MAX_SINGLE_UPLOAD_BYTES:
        raise IngestionSafetyError("ZIP archive exceeds the 200 MB intake limit")
    if depth > MAX_ARCHIVE_DEPTH:
        raise IngestionSafetyError("Nested ZIP depth exceeds the supported safety limit")

    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise IngestionSafetyError("The uploaded ZIP archive is corrupt or unsupported") from exc

    infos = [info for info in archive.infolist() if not info.is_dir()]
    if len(infos) > MAX_ARCHIVE_MEMBERS:
        raise IngestionSafetyError(f"ZIP archive contains more than {MAX_ARCHIVE_MEMBERS} files")

    total = sum(int(info.file_size) for info in infos)
    if total > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
        raise IngestionSafetyError("ZIP archive expands beyond the 500 MB uncompressed safety limit")

    items: list[ArchiveItem] = []
    try:
        for info in infos:
            path = _check_member(info)
            member_data = archive.read(info)
            nested: tuple[ArchiveItem, ...] = ()
            if path.suffix.lower() == ".zip":
                if depth >= MAX_ARCHIVE_DEPTH:
                    raise IngestionSafetyError("Nested ZIP depth exceeds the supported safety limit")
                nested_inspection = inspect_zip(member_data, depth=depth + 1)
                nested = nested_inspection.items
            items.append(
                ArchiveItem(
                    path=path.as_posix(),
                    filename=path.name,
                    data=member_data,
                    nested=nested,
                )
            )
    finally:
        archive.close()

    return ArchiveInspection(items=tuple(items), file_count=len(items), total_uncompressed_bytes=total)


def google_drive_target(raw_url: str) -> tuple[str, str]:
    value = raw_url.strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in {"drive.google.com", "docs.google.com"}:
        raise ValueError("Use an https://drive.google.com or https://docs.google.com file link.")

    parts = [part for part in parsed.path.split("/") if part]
    file_id = None
    kind = None
    if parsed.hostname == "docs.google.com" and len(parts) >= 3 and parts[1] == "d":
        kind = parts[0]
        file_id = parts[2]
    elif parsed.hostname == "drive.google.com":
        if len(parts) >= 3 and parts[0] == "file" and parts[1] == "d":
            file_id = parts[2]
        else:
            file_id = parse_qs(parsed.query).get("id", [None])[0]

    if not file_id or not _GOOGLE_FILE_ID_RE.match(file_id):
        raise ValueError("That link does not contain a supported Google Drive file ID.")

    short_id = file_id[:8]
    if kind == "document":
        return f"https://docs.google.com/document/d/{file_id}/export?format=pdf", f"google-doc-{short_id}.pdf"
    if kind == "spreadsheets":
        return f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx", f"google-sheet-{short_id}.xlsx"
    if kind == "presentation":
        return f"https://docs.google.com/presentation/d/{file_id}/export?format=pptx", f"google-slides-{short_id}.pptx"
    if kind is not None:
        raise ValueError("That Google file type is not supported for direct import yet.")
    return f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t", f"google-drive-{short_id}"


def download_google_drive_file(raw_url: str) -> tuple[str, bytes]:
    download_url, default_name = google_drive_target(raw_url)
    request = Request(download_url, headers={"User-Agent": "ColettiOS-Universal-Ingestion/1.0"})
    try:
        with urlopen(request, timeout=30) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_SINGLE_UPLOAD_BYTES:
                raise ValueError("Google Drive file exceeds the 200 MB intake limit.")
            data = response.read(MAX_SINGLE_UPLOAD_BYTES + 1)
            if len(data) > MAX_SINGLE_UPLOAD_BYTES:
                raise ValueError("Google Drive file exceeds the 200 MB intake limit.")
            if (response.headers.get("Content-Type") or "").lower().startswith("text/html"):
                raise ValueError("Google returned an access page instead of the file. Check sharing/access and try again.")
            disposition = response.headers.get("Content-Disposition") or ""
            match = re.search(r'filename="?([^";]+)', disposition, flags=re.IGNORECASE)
            filename = match.group(1).strip() if match else default_name
            return filename, data
    except HTTPError as exc:
        raise ValueError(f"Google Drive returned HTTP {exc.code}; verify the file sharing setting.") from exc
    except URLError as exc:
        raise ValueError("ColettiOS could not reach Google Drive from this runtime.") from exc
