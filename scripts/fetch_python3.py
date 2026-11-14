#!/usr/bin/env python3
"""Python 3.11 and hildonlite for the N900 from the apt repository of the project, unpacked into ./sysroot/opt/python3 (no cross-build).

The emulator (scripts/hildon-run.sh) runs Python 3 GUI programs with the ARM interpreter under qemu-user. Cross-building it takes an hour (apps/python3
in nokia-n900-apps); the same interpreter is in the repository as the package python3.11, and hildonlite (Hildon windows through ctypes) as python3-hildonlite.
This script reads the index of the repository, takes the newest version of the packages and of the packages of the same repository they depend on,
checks the SHA-256 sums and unpacks them (dpkg-deb -x) into the sysroot, where the emulator expects /opt/python3 (the same place as on the phone).

Usage (inside the Workshop: make arm-python):
    scripts/fetch_python3.py                      # python3.11 and python3-hildonlite
    scripts/fetch_python3.py --dry-run            # what would be downloaded
    scripts/fetch_python3.py --force              # unpack again although the same versions are there
    scripts/fetch_python3.py PACKAGE ...          # other packages of the repository (for example curl)
"""
import argparse
import gzip
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_sysroot import newest, parse_packages  # noqa: E402  (the index parser and the version order of the sysroot script)

REPO = "https://n900-resurrection.github.io/n900-repository"
INDEX = "dists/fremantle/main/binary-armel/Packages.gz"
DEFAULT = ["python3.11", "python3-hildonlite"]
UA = {"User-Agent": "n900-devkit/0.1 (+https://github.com/n900-resurrection/n900-devkit)"}


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def dependencies(stanza, index):
    """Names of the packages of this repository that a package depends on (the system ones, libc6 and so on, are on the phone and in the sysroot)."""
    out = []
    for field in ("Depends", "Pre-Depends"):
        for part in stanza.get(field, "").split(","):
            for alt in part.split("|"):
                name = re.sub(r"\s*\(.*?\)", "", alt).strip()
                if name in index:
                    out.append(name)
                    break
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("packages", nargs="*", help=f"packages of the repository (default: {' '.join(DEFAULT)})")
    ap.add_argument("--repo", default=REPO, help="address of the apt repository")
    ap.add_argument("--sysroot", default="sysroot")
    ap.add_argument("--cache", default="downloads")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    index = parse_packages(gzip.decompress(fetch(f"{a.repo}/{INDEX}")).decode("utf-8", "replace"))
    chosen, queue = {}, list(a.packages or DEFAULT)
    while queue:
        name = queue.pop(0)
        if name in chosen:
            continue
        if name not in index:
            sys.exit(f"{name} is not in the repository {a.repo}")
        chosen[name] = newest(index[name])
        queue += dependencies(chosen[name], index)

    sysroot, cache = Path(a.sysroot), Path(a.cache)
    stamp = sysroot / "opt" / "python3" / ".devkit-packages.json"
    want = {n: s["Version"] for n, s in chosen.items()}
    print("packages:", ", ".join(f"{n} {v}" for n, v in want.items()))
    if a.dry_run:
        return
    if not a.force and stamp.exists() and json.loads(stamp.read_text()).get("packages") == want:
        print(f"already in {sysroot}/opt/python3 (use --force to unpack again)")
        return
    cache.mkdir(parents=True, exist_ok=True)
    sysroot.mkdir(parents=True, exist_ok=True)
    for name, s in chosen.items():
        deb = cache / Path(s["Filename"]).name
        if not deb.exists():
            print(f"downloading {name} {s['Version']} ({int(s.get('Size', 0)) // 1024} kB)")
            data = fetch(f"{a.repo}/{s['Filename']}")
            if s.get("SHA256") and hashlib.sha256(data).hexdigest() != s["SHA256"]:
                sys.exit(f"the SHA-256 sum of {deb.name} differs from the index")
            deb.write_bytes(data)
        subprocess.run(["dpkg-deb", "-x", str(deb), str(sysroot)], check=True)
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(json.dumps({"packages": want}, indent=1) + "\n")
    py = sysroot / "opt" / "python3" / "bin" / "python3.11"
    print(f"Done: {py} ({'found' if py.exists() else 'MISSING'})")


if __name__ == "__main__":
    main()
