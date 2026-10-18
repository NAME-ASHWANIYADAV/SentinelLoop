"""Fetch CARE to Compare v6 (Zenodo 15846963, CC BY-SA 4.0) for G0 - run ONLY after the download is approved.

Downloads CARE_To_Compare.zip (5,503,439,673 bytes) into data/external/care_v6/ (git-ignored), resuming if partial,
verifies the MD5 published by Zenodo (2547b58c21ac8c242d13232860cf500c) and records a SHA-256. The archive is treated
as untrusted: its member list is checked (no absolute paths, no '..', no links, size limits) and only .csv/.txt/.md
members are extracted into data/external/care_v6/extracted/. Nothing from the archive is executed.

Usage:  python -I product/scripts/fetch_care.py [--check-only] [--max-free-gb-needed 14]
"""
import argparse
import hashlib
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "data" / "external" / "care_v6"
URL = "https://zenodo.org/records/15846963/files/CARE_To_Compare.zip?download=1"
SIZE, MD5 = 5_503_439_673, "2547b58c21ac8c242d13232860cf500c"
ALLOWED = (".csv", ".txt", ".md")
MAX_MEMBER = 3 * 1024 ** 3


def download(path: Path):
    have = path.stat().st_size if path.exists() else 0
    if have == SIZE:
        return
    req = urllib.request.Request(URL, headers={"Range": f"bytes={have}-", "User-Agent": "SentinelLoop-G0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "ab" if have else "wb") as f:
        if have and r.status != 206:
            raise SystemExit("server ignored the range request; delete the partial file and retry")
        done = have
        while True:
            chunk = r.read(8 * 1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            print(f"\r{done / 1e9:.2f} / {SIZE / 1e9:.2f} GB", end="", flush=True)
    print()
    if path.stat().st_size != SIZE:
        raise SystemExit(f"size {path.stat().st_size} != {SIZE}")


def digests(path: Path):
    md5, sha = hashlib.md5(), hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(16 * 1024 * 1024), b""):
            md5.update(chunk)
            sha.update(chunk)
    return md5.hexdigest(), sha.hexdigest()


def safe_members(z: zipfile.ZipFile):
    out, refused = [], []
    for info in z.infolist():
        name = info.filename
        p = PurePosixPath(name)
        is_link = (info.external_attr >> 16) & 0o170000 == 0o120000
        if name.startswith(("/", "\\")) or ".." in p.parts or ":" in name or is_link:
            refused.append((name, "unsafe path or link"))
        elif info.is_dir():
            continue
        elif not name.lower().endswith(ALLOWED):
            refused.append((name, "type not extracted"))
        elif info.file_size > MAX_MEMBER:
            refused.append((name, "member too large"))
        else:
            out.append(info)
    return out, refused


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true", help="verify an already downloaded zip and list it; no network")
    ap.add_argument("--max-free-gb-needed", type=float, default=14.0)
    a = ap.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    zpath = DEST / "CARE_To_Compare.zip"
    free = shutil.disk_usage(DEST).free / 1e9
    if not a.check_only and free < a.max_free_gb_needed:
        raise SystemExit(f"only {free:.1f} GB free; need about {a.max_free_gb_needed} GB (zip + extraction)")
    if not a.check_only:
        download(zpath)
    md5, sha = digests(zpath)
    if md5 != MD5:
        raise SystemExit(f"MD5 mismatch: {md5} != {MD5}; refusing to use the file")
    with zipfile.ZipFile(zpath) as z:
        members, refused = safe_members(z)
        out = DEST / "extracted"
        for info in members:
            target = (out / info.filename).resolve()
            if out.resolve() not in target.parents:
                refused.append((info.filename, "escapes the extraction directory"))
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst, 16 * 1024 * 1024)
    manifest = {"source": URL, "licence": "CC BY-SA 4.0", "bytes": SIZE, "md5": md5, "sha256": sha, "extracted": len(members),
                "refused": refused[:200], "n_refused": len(refused)}
    (DEST / "fetch_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k != "refused"}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
