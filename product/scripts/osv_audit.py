"""Query the OSV vulnerability database (api.osv.dev) for every pinned package in requirements.lock.txt.

Sends only package names and versions. Output: product/evidence/security/osv_audit.{json,md}. Exit 1 if any
known vulnerability affects a pinned version.
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "product" / "evidence" / "security"


def pins():
    out = []
    for line in (ROOT / "requirements.lock.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Za-z0-9_.\-]+)==([^\s;#]+)", line.strip())
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main():
    pk = pins()
    res = post("https://api.osv.dev/v1/querybatch", {"queries": [{"package": {"name": n, "ecosystem": "PyPI"}, "version": v} for n, v in pk]})
    findings = []
    for (name, ver), r in zip(pk, res["results"]):
        for v in r.get("vulns", []) or []:
            detail = {}
            try:
                with urllib.request.urlopen(f"https://api.osv.dev/v1/vulns/{v['id']}", timeout=60) as rr:
                    detail = json.loads(rr.read())
            except Exception as e:
                detail = {"error": type(e).__name__}
            fixed = sorted({ev.get("fixed") for a in detail.get("affected", []) for rg in a.get("ranges", []) for ev in rg.get("events", []) if ev.get("fixed")})
            findings.append({"package": name, "version": ver, "id": v["id"], "aliases": detail.get("aliases", []),
                             "summary": (detail.get("summary") or detail.get("details", "")[:200]), "fixed_in": fixed})
    out = {"queried_at": datetime.now(timezone.utc).isoformat(), "source": "https://api.osv.dev (OSV.dev)", "packages": len(pk), "findings": findings}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "osv_audit.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    lines = [f"# OSV audit of requirements.lock.txt (generated {out['queried_at']})", "", f"Packages queried: {len(pk)}. Findings: {len(findings)}.", ""]
    if findings:
        lines += ["| package | pinned | advisory | aliases | fixed in | summary |", "|---|---|---|---|---|---|"]
        lines += [f"| {f['package']} | {f['version']} | {f['id']} | {', '.join(f['aliases'][:3])} | {', '.join(f['fixed_in'][:3])} | {f['summary'][:120]} |" for f in findings]
    (OUT / "osv_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
