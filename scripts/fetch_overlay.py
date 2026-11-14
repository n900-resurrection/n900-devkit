#!/usr/bin/env python3
"""The runtime files of the emulator that the SDK sysroot lacks, WITHOUT a phone: downloaded from the Maemo mirrors (the same ones as the sysroot).

`make hildon-overlay` copies the theme, the fonts, the icons and more from your own N900 (the exact look of the phone). Without a phone this script gets
what is free to download:
  - the locale archive of glibc 2.5 (package posix-locales): UTF-8 locales, programs such as tmux need it under qemu-user (`make locale-overlay`),
  - the Hildon icons (osso-icons-default), fontconfig, the pango modules and their list, the GTK engine sapwood and the stock GTK2 themes,
  - fonts: DejaVu Sans from the host (the Nokia fonts and the Nokia themes alpha and beta are in the Maemo SDK repository `nokia-binaries`, under the
    licence of Nokia, and the public mirrors do not serve them), and a stand-in theme of the kit (theme/devkit: dark, orange selection, plain GTK drawing).
The emulator then looks close to the phone but not the same: the widgets are not drawn with the pixmaps of the Nokia theme. For the exact look use
`make hildon-overlay DEVICE=user@address` once with your own phone: the theme `beta`, if present in the sysroot, wins over the stand-in.

Usage (inside the Workshop: make hildon-overlay-download / make locale-overlay):
    scripts/fetch_overlay.py            # everything
    scripts/fetch_overlay.py --locale   # only the locale archive
    scripts/fetch_overlay.py --dry-run
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_sysroot as FS  # noqa: E402  (the index of the mirrors, the version order, the download with the MD5 check)

LOCALE = ["posix-locales"]
HILDON = ["osso-icons-default", "fontconfig", "libpango1.0-common", "libpango1.0-0", "gtk2-engines-sapwood", "libgtk2.0-common"]
HOST_FONTS = Path("/usr/share/fonts/truetype/dejavu")
KIT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--locale", action="store_true", help="only the locale archive")
    ap.add_argument("--sysroot", default="sysroot")
    ap.add_argument("--cache", default="downloads")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    names = LOCALE if a.locale else LOCALE + HILDON
    pkgs = FS.load_index()
    chosen = {}
    for n in names:
        if n not in pkgs:
            sys.exit(f"{n} is not in the index of the mirrors")
        chosen[n] = FS.newest(pkgs[n])
    total = sum(int(s.get("Size", 0)) for s in chosen.values())
    print(f"packages: {', '.join(f'{n} {s['Version']}' for n, s in chosen.items())} ({total / 1048576:.1f} MB)")
    if a.dry_run:
        return
    cache, sysroot = Path(a.cache), Path(a.sysroot)
    cache.mkdir(parents=True, exist_ok=True)
    sysroot.mkdir(parents=True, exist_ok=True)
    for n, s in chosen.items():
        deb = cache / Path(s["Filename"]).name
        if not deb.exists():
            print(f"downloading {n} {s['Version']}")
            deb.write_bytes(FS.download(s))
            time.sleep(FS.DELAY)
        subprocess.run(["dpkg-deb", "-x", str(deb), str(sysroot)], check=True)
    if a.locale:
        print(f"locale archive: {sysroot / 'usr/lib/locale/locale-archive'}")
        return
    # The files of packages that were unpacked as they come: symbolic links inside the sysroot are made relative (qemu-user resolves absolute ones on the host)
    FS.fix_symlinks(sysroot)
    # The list of the pango modules: the package carries an empty one (the phone makes it when the package is installed), without the entry of the
    # basic engine every text is drawn as empty boxes. pango-querymodules (ARM) runs under qemu-user inside the sysroot.
    mods = sorted(p.name for p in (sysroot / "usr/lib/pango/1.6.0/modules").glob("*.so"))
    env = {"QEMU_LD_PREFIX": str(sysroot.resolve()), "LC_ALL": "C", "PATH": "/usr/bin:/bin"}
    q = subprocess.run(["qemu-arm", str((sysroot / "usr/bin/pango-querymodules").resolve())] + [f"/usr/lib/pango/1.6.0/modules/{m}" for m in mods],
                       capture_output=True, text=True, env=env)
    if q.returncode == 0 and "BasicScriptEngineFc" in q.stdout:
        (sysroot / "etc/pango").mkdir(parents=True, exist_ok=True)
        (sysroot / "etc/pango/pango.modules").write_text(q.stdout)
        print(f"pango: the list of {len(mods)} modules made with pango-querymodules")
    else:
        sys.exit("pango-querymodules failed (is qemu-user installed? make toolchain): " + (q.stderr or q.stdout)[-300:])
    # Fonts: DejaVu Sans of the host (the container of the Workshop has it); the Nokia fonts need the phone (make hildon-overlay DEVICE=...)
    fonts = sysroot / "usr/share/fonts/truetype/dejavu"
    if HOST_FONTS.is_dir():
        fonts.mkdir(parents=True, exist_ok=True)
        for f in HOST_FONTS.glob("DejaVuSans*.ttf"):
            shutil.copy2(f, fonts / f.name)
        print(f"fonts: DejaVu Sans copied from the host ({len(list(fonts.glob('*.ttf')))} files)")
    else:
        print("WARNING: no DejaVu fonts in", HOST_FONTS, "(apt install fonts-dejavu-core), the programs would draw no text")
    # The stand-in theme of the kit (it is used when the sysroot has neither beta nor alpha)
    theme = KIT / "theme" / "devkit"
    dst = sysroot / "usr/share/themes/devkit"
    shutil.copytree(theme, dst, dirs_exist_ok=True)
    print(f"theme: the stand-in theme is in {dst} (the exact look: make hildon-overlay DEVICE=... from a phone)")
    print("Done.")


if __name__ == "__main__":
    main()
