#!/usr/bin/env python3
"""Build a sysroot for Maemo 5 (Fremantle, armel, glibc 2.5) from the SDK repository.

Takes the packages from OUR mirror of the SDK first (OWN below, a GitHub Pages site; the same layout as repository.maemo.org), so that the
slow third-party mirrors are not loaded again and again. What our mirror lacks is taken from the old mirrors (maemo.plan9.de, then
maemo.viniciuspaes.com), and when a writable copy of our mirror is at hand (the folder sdk-mirror/, a git clone, or --mirror DIR), the .deb files and their
index entries are added to it: commit and push it, and the next clone finds the package at home. Dependencies of the requested packages
are resolved, only the needed .deb files are downloaded and unpacked into ./sysroot (via dpkg-deb -x). It does not download the whole mirror.

Usage:
    scripts/fetch_sysroot.py                       # default set of -dev packages
    scripts/fetch_sysroot.py libgtk2.0-dev zlib1g-dev
    scripts/fetch_sysroot.py --dry-run             # only print what would be downloaded
    scripts/fetch_sysroot.py --list libncurses     # search the index
    scripts/fetch_sysroot.py --mirror-only         # only fill sdk-mirror/ (no unpacking)

Status: verified by cross-compiling and running programs on a real N900 (2026-11).
See DOC/workshop-crosscompile.md.
"""
import argparse
import hashlib
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# Mirrors of repository.maemo.org in the order of use (DOC/mirror.md): the index is read from the first one that answers, a .deb that one cannot
# deliver is taken from the next. Both have the same layout (dists/, pool/). maemo.viniciuspaes.com refuses generic User-Agents (curl, Python-urllib),
# so every request names this tool; it also asks not to be mirrored in bulk: we take only the files that are needed.
BASES = [
    "http://maemo.plan9.de/apt-mirror/mirror/repository.maemo.org/",
    "http://maemo.viniciuspaes.com/",
]
BASE = BASES[0]
# Our mirror of the packages the sysroot needs (repository n900-resurrection/n900-sdk-mirror): pool/ and dists/ as above, plus the file MISSING with the names
# that the SDK does not have (virtual packages, translations), so that a complete set is known without asking the old mirrors.
OWN = "https://n900-resurrection.github.io/n900-sdk-mirror/"
MIRROR_DIR = "sdk-mirror"
# Fremantle SDK: dists/fremantle/sdk/{free,non-free}/binary-armel/Packages
INDEXES = [
    "dists/fremantle/sdk/free/binary-armel/Packages",
    "dists/fremantle/sdk/non-free/binary-armel/Packages",
]
DEFAULT_ROOTS = [
    "ncurses-base",   # terminfo data (/etc/terminfo), so that curses programs can run under qemu
    "libc6-dev",
    "zlib1g-dev",
    "libncurses5-dev",
    "libncursesw5-dev",
    "libssl-dev",
    "libglib2.0-dev",
    "libgtk2.0-dev",
    "libhildon1-dev",
    "libsdl1.2-dev",
    "libreadline5-dev",
    # SDL 2 (apps/sdl2): sound through ALSA or PulseAudio, X11 extensions (all are loaded at run time and optional)
    "libasound2-dev",
    "libpulse-dev",
    "libxrandr-dev",
    "libxcursor-dev",
    "libxi-dev",
    "libxfixes-dev",
]
DELAY = 0.3  # seconds between downloads, to go easy on somebody else's server


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "n900-sysroot-fetch/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def download(stanza, bases=BASES) -> bytes:
    """The .deb of a package from the first mirror that has it; the MD5 sum of the index is checked (a third-party mirror)."""
    last = None
    for base in bases:
        try:
            data = fetch(base + stanza["Filename"])
        except Exception as e:  # noqa: BLE001
            print(f"WARNING: {base}: {e}", file=sys.stderr)
            last = e
            continue
        want = stanza.get("MD5sum")
        if want and hashlib.md5(data).hexdigest() != want:
            print(f"WARNING: {base}: MD5 sum of {stanza['Filename']} differs from the index, trying the next mirror", file=sys.stderr)
            continue
        return data
    sys.exit(f"Could not download {stanza['Filename']}: {last}")


def parse_packages(text: str):
    """Return {name: [stanza, ...]} (the index holds several versions of the same package)."""
    pkgs = {}
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        fields = {}
        key = None
        for line in block.splitlines():
            if line[:1] in (" ", "\t") and key:
                fields[key] += "\n" + line
            elif ":" in line:
                key, _, val = line.partition(":")
                fields[key] = val.strip()
        if "Package" in fields:
            pkgs.setdefault(fields["Package"], []).append(fields)
    return pkgs


def vercmp(a: str, b: str) -> int:
    if subprocess.run(["dpkg", "--compare-versions", a, "gt", b]).returncode == 0:
        return 1
    if subprocess.run(["dpkg", "--compare-versions", a, "lt", b]).returncode == 0:
        return -1
    return 0


def newest(stanzas):
    best = stanzas[0]
    for s in stanzas[1:]:
        if vercmp(s["Version"], best["Version"]) > 0:
            best = s
    return best


def dep_names(stanza):
    out = []
    for field in ("Depends", "Pre-Depends"):
        for part in stanza.get(field, "").split(","):
            part = part.strip()
            if not part:
                continue
            alts = [re.sub(r"\s*\(.*?\)", "", a).strip() for a in part.split("|")]
            out.append(alts)
    return out


def load_index():
    pkgs = {}
    for rel in INDEXES:
        data = None
        for base in BASES:
            url = base + rel
            try:
                data = fetch(url)
                break
            except Exception as e:  # noqa: BLE001
                print(f"WARNING: {url}: {e}", file=sys.stderr)
        if data is None:
            continue
        for name, lst in parse_packages(data.decode("utf-8", "replace")).items():
            pkgs.setdefault(name, []).extend(lst)
    if not pkgs:
        sys.exit("Could not load the package index.")
    return pkgs


def section_of(stanza) -> str:
    """free / non-free, from the pool path (pool/maemo5.0/free/d/dbus/...)."""
    return stanza["Filename"].split("/")[2]


def load_own(mirror):
    """The index of our mirror: the local copy when there is one (it may hold what is not pushed yet), otherwise the published one."""
    pkgs = {}
    for rel in INDEXES:
        local = mirror / rel if mirror else None
        if local and local.is_file():
            text = local.read_text()
        else:
            try:
                text = fetch(OWN + rel).decode("utf-8", "replace")
            except Exception:  # noqa: BLE001  (the mirror does not exist yet or is not reachable: everything comes from the old mirrors)
                continue
        for name, lst in parse_packages(text).items():
            for st in lst:
                st["_own"] = "1"
            pkgs.setdefault(name, []).extend(lst)
    return pkgs


def load_missing(mirror):
    """Names the SDK does not have (the file MISSING of our mirror, local or published)."""
    try:
        text = (mirror / "MISSING").read_text() if mirror and (mirror / "MISSING").is_file() else fetch(OWN + "MISSING").decode()
    except Exception:  # noqa: BLE001
        return set()
    return {l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")}


def write_mirror(mirror, new, missing):
    """Add the stanzas of the newly mirrored packages to the Packages files and the unknown names to MISSING."""
    for rel in INDEXES:
        sec = rel.split("/")[3]
        add = [st for st in new if section_of(st) == sec]
        if not add:
            continue
        path = mirror / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        have = parse_packages(path.read_text()) if path.is_file() else {}
        for st in add:
            have[st["Package"]] = [x for x in have.get(st["Package"], []) if x["Version"] != st["Version"]] + [st]
        blocks = []
        for name in sorted(have):
            for st in have[name]:
                blocks.append("\n".join(f"{k}: {v}" for k, v in st.items() if not k.startswith("_")))
        path.write_text("\n\n".join(blocks) + "\n")
    if missing:
        path = mirror / "MISSING"
        names = load_missing(mirror) | missing
        path.write_text("# Names that the SDK repository does not have (virtual packages, translations): not looked up again.\n" + "\n".join(sorted(names)) + "\n")


def resolve(pkgs, roots):
    chosen, queue, missing = {}, list(roots), set()
    while queue:
        name = queue.pop(0)
        if name in chosen:
            continue
        if name not in pkgs:
            missing.add(name)
            continue
        st = newest(pkgs[name])
        chosen[name] = st
        for alts in dep_names(st):
            pick = next((a for a in alts if a in pkgs), None)
            if pick:
                queue.append(pick)
            else:
                missing.add(alts[0])
    return chosen, missing


def fix_symlinks(sysroot: Path) -> int:
    """Rewrite absolute symlinks (e.g. usr/lib/libm.so -> /lib/libm.so.6) as relative ones.

    The packages assume that "/" is the root of the device. Outside of it such a link would
    point to the host and the linker would report "cannot open ... libm.so". Only links whose
    target exists inside the sysroot are rewritten.
    """
    root = sysroot.resolve()
    n = 0
    for p in root.rglob("*"):
        if not p.is_symlink():
            continue
        target = Path(p.readlink())
        if not target.is_absolute():
            continue
        dest = root / str(target).lstrip("/")
        if not (dest.exists() or dest.is_symlink()):
            continue
        rel = Path(os.path.relpath(dest, p.parent))
        p.unlink()
        p.symlink_to(rel)
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="*", help="root packages (default: DEFAULT_ROOTS)")
    ap.add_argument("--sysroot", default="sysroot", help="target directory (default ./sysroot)")
    ap.add_argument("--cache", default="downloads", help="download cache for .deb files (default ./downloads)")
    ap.add_argument("--mirror", default=os.environ.get("SDK_MIRROR", MIRROR_DIR), metavar="DIR",
                    help=f"writable copy of our mirror, filled with what had to be taken from the old mirrors (default ./{MIRROR_DIR} when it exists)")
    ap.add_argument("--mirror-only", action="store_true", help="only fill the mirror directory, do not unpack")
    ap.add_argument("--dry-run", action="store_true", help="only print the plan")
    ap.add_argument("--list", metavar="TEXT", help="list packages with TEXT in the name and exit")
    a = ap.parse_args()

    mirror = Path(a.mirror) if Path(a.mirror).is_dir() else None
    if a.mirror_only and not mirror:
        sys.exit(f"--mirror-only needs the directory {a.mirror} (a clone of n900-sdk-mirror, or --mirror DIR)")
    roots = a.roots or DEFAULT_ROOTS

    # Our mirror first; the old mirrors are asked (index and all) only for what it does not know.
    own = load_own(mirror)
    chosen, missing = resolve(own, roots)
    newly_missing = missing - load_missing(mirror)
    pkgs = own
    if newly_missing or a.list:
        up = load_index()
        pkgs = {**up, **own}  # our packages win by name, also over a newer version of the old mirror
        if a.list:
            for n in sorted(pkgs):
                if a.list in n:
                    print(n, newest(pkgs[n])["Version"])
            return
        chosen, missing = resolve(pkgs, roots)
        newly_missing = missing - load_missing(mirror)
    total = sum(int(s.get("Size", 0)) for s in chosen.values())
    n_own = sum(1 for s in chosen.values() if s.get("_own"))
    print(f"Packages: {len(chosen)} ({n_own} from our mirror), approximately {total / 1048576:.1f} MB")
    if missing:
        print("Not found in the index (skipped):", ", ".join(sorted(missing)))
    if a.dry_run:
        for n, s in sorted(chosen.items()):
            print(f"  {n} {s['Version']}{'' if s.get('_own') else '  (old mirror)'}")
        return

    cache, sysroot = Path(a.cache), Path(a.sysroot)
    cache.mkdir(parents=True, exist_ok=True)
    if not a.mirror_only:
        sysroot.mkdir(parents=True, exist_ok=True)
    added = []
    try:
        for n, s in sorted(chosen.items()):
            rel = Path(s["Filename"])
            in_mirror = mirror / rel if mirror else None
            deb = cache / rel.name
            if in_mirror and in_mirror.is_file():
                deb = in_mirror
            elif not deb.exists():
                print(f"downloading {n} {s['Version']}" + ("" if s.get("_own") else " (old mirror)"))
                deb.write_bytes(download(s, [OWN] + BASES if s.get("_own") else BASES))
                if not s.get("_own"):
                    time.sleep(DELAY)
            if mirror and not s.get("_own"):
                # a package of the old mirrors: its own copy goes into our mirror (to be committed)
                if not in_mirror.is_file():
                    in_mirror.parent.mkdir(parents=True, exist_ok=True)
                    in_mirror.write_bytes(deb.read_bytes())
                added.append(s)
            if not a.mirror_only:
                subprocess.run(["dpkg-deb", "-x", str(deb), str(sysroot)], check=True)
    finally:
        if mirror and (added or newly_missing):
            write_mirror(mirror, added, newly_missing)
            print(f"Added to {mirror}/: {len(added)} package(s), {len(newly_missing)} unknown name(s): commit and push it.")
    if a.mirror_only:
        return
    fixed = fix_symlinks(sysroot)
    print(f"Absolute symlinks rewritten as relative: {fixed}")
    print(f"Done: {sysroot.resolve()}")


if __name__ == "__main__":
    main()
