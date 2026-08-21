"""Build the downloadable archive containing every web map resource."""

from __future__ import annotations

import hashlib
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAPS = ROOT / "docs" / "data" / "maps"
OUTPUT = ROOT / "data" / "releases" / "maps"
ARCHIVE = OUTPUT / "china_prefecture_crosswalk_web_maps_v4.0.zip"
FIXED_DATE = (2026, 8, 20, 0, 0, 0)


def info(name: str) -> zipfile.ZipInfo:
    item = zipfile.ZipInfo(name, FIXED_DATE)
    item.compress_type = zipfile.ZIP_DEFLATED
    item.external_attr = 0o644 << 16
    return item


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(MAPS.rglob("*")):
            if path.is_file():
                archive.writestr(info(str(Path("maps") / path.relative_to(MAPS))), path.read_bytes())
        for name in ("README.md", "NOTICE.md"):
            path = OUTPUT / name
            archive.writestr(info(name), path.read_bytes())
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    (OUTPUT / "china_prefecture_crosswalk_web_maps_v4.0.sha256").write_text(f"{digest}  {ARCHIVE.name}\n", encoding="utf-8")
    print(f"files={len(zipfile.ZipFile(ARCHIVE).namelist())} size_mb={ARCHIVE.stat().st_size / 1024 / 1024:.1f}")


if __name__ == "__main__":
    main()
