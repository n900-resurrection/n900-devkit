# n900-devkit

Everything you need to **write and try an application for the Nokia N900 (Maemo 5, armel, glibc 2.5) on a PC**, without cloning the whole
[nokia-n900-apps](https://github.com/n900-resurrection/nokia-n900-apps) repository:

- a **Workshop** (a container, Ubuntu 24.04) with the armel cross toolchain (`scripts/maemo-gcc`) and `qemu-user`,
- the **Fremantle sysroot** of the Maemo 5 SDK (`make sysroot`),
- an **emulated Hildon desktop**: your GTK2/Hildon program (Python 3 with [hildonlite](https://github.com/n900-resurrection/hildonlite), Python 2.5 with PyGTK, or a C program)
  runs under `qemu-user` against the real GTK 2.14 / Hildon libraries on a virtual 800x480 screen, with a top bar, task switcher and launcher like the N900's,
- test scripts that run in an emulated phone (`make emu-test`).

Nothing from Nokia is stored in this repository, and **no phone is needed**: the sysroot, the ARM Python and the runtime files of the emulator are downloaded
(from the community mirrors of Maemo and the apt repository of the project). With a phone you can get the exact look (below).

- [n900-devkit](#n900-devkit)
  - [Quick start](#quick-start)
  - [Your own application](#your-own-application)
  - [With and without a phone](#with-and-without-a-phone)
  - [What is where](#what-is-where)
  - [Use in the main repository](#use-in-the-main-repository)
  - [Licence](#licence)


## Documentation
- [docs/getting-started.md](docs/getting-started.md): install, the first run, with and without a phone, starting over, troubleshooting
- [docs/python-gui.md](docs/python-gui.md): write a GUI application in Python 3 (hildonlite) and try it in the emulator; the example `apps/quick-notes`
- [docs/emulator.md](docs/emulator.md): the emulated desktop, your application in it, tests and screenshots, limits
- [docs/cross-compile.md](docs/cross-compile.md): the sysroot, the compiler wrapper, building C programs for Maemo 5

## Quick start

You need Ubuntu (or another Linux) with [Workshop](https://snapcraft.io/workshop) and LXD (`sudo snap install --channel=6/stable lxd`, `sudo snap install --classic workshop`, `lxd init`).

```sh
git clone https://github.com/n900-resurrection/n900-devkit.git
cd n900-devkit
make up toolchain sysroot            # the container, the toolchain, the sysroot (once, a few hundred MB)
make hello                           # build and run a C program for the N900 under qemu-user
make arm-python                      # Python 3.11 and hildonlite for the N900, from the apt repository of the project (no cross-build)
make hildon-overlay                  # icons, fontconfig, pango and more from the Maemo mirrors + a stand-in theme (once; no phone needed)
make locale-overlay                  # the glibc 2.5 locale archive, downloaded (needed by programs such as tmux)
make hildon-run SCRIPT=src/python3/hildon/proof.py SHOT=build/shot.png   # a Hildon program on the virtual screen, screenshot after 6 s
make emulator                        # the whole emulated desktop, VNC on port 5999 of the container
```

`make` without arguments lists the targets.

| Target | What it does |
|---|---|
| `up`, `down`, `status`, `enter` | create/start, stop, show and enter the Workshop |
| `toolchain` | install the armel cross toolchain and `qemu-user` in it |
| `sysroot` | download the Fremantle SDK sysroot into `./sysroot` (only the needed packages) |
| `arm-python` | download Python 3.11 and `python3-hildonlite` (and what they need) from the [apt repository](https://n900-resurrection.github.io/) into `sysroot/opt/python3`; `hildon-run` uses it |
| `hello` | build and run `src/c/hello/hello.c` (qemu-user, glibc 2.5) |
| `hildon-overlay` | the runtime files of the emulator into the sysroot: without a phone downloaded (icons, fontconfig, pango, the GTK engine, DejaVu fonts of the host, the stand-in theme of the kit); with `DEVICE=user@address` copied from your own N900 (the Nokia theme and fonts, Python 2.5) |
| `hildon-overlay-download` | the download variant explicitly |
| `locale-overlay` | the locale archive (UTF-8 locales, glibc 2.5; programs such as tmux need it under qemu-user): downloaded, or from the phone with `DEVICE=...` |
| `hildon-run` | show a GTK2/Hildon program: `SCRIPT=file.py`, `APP=<app>` (an application with `apps/<app>/hildon-run.sh`), `SHOT=file.png`, `VNC=1`, `PY2=1` |
| `emulator`, `emulator-stop` | start/stop the emulated desktop (top bar, launcher, task switching) |
| `clean` | remove `build/` (the emulator root, screenshots, programs built by the scripts) |
| `clean-all` | back to nothing: remove `build/`, `sysroot/`, `downloads/` and the Workshop container (asks first, `YES=1` skips the question); then `make up toolchain sysroot ...` starts from scratch |
| `emu-test`, `emu-shots` | run the tests of applications in an emulated phone, take screenshots from a timeline |

## Your own application
Put it in `apps/<name>/` of the kit (`APPS_DIR=<dir>` in the environment or on the command line changes the directory; relative to the project). The emulator knows an application when
`apps/<name>/hildon-run.sh` exists (it sets `RUN_SCRIPT` and may prepare demo data, for example a home directory in `/tmp`; see the examples in nokia-n900-apps, `apps/mutt-hildon`):

```sh
# apps/myapp/hildon-run.sh
# Name: My application
RUN_SCRIPT=/project/apps/myapp/myapp.py
```

`make hildon-run APP=myapp SHOT=build/myapp.png` starts it in the desktop with the top bar, `make emulator` shows all such applications in the launcher; `apps/myapp/test.sh` and
`shots.txt` are used by `make emu-test` and `make emu-shots`. Other settings of the scripts (environment): `PROJ` (the project in the Workshop, `/project`), `SYSROOT`, `DEB_DIR`
(built `.deb` packages that the launcher offers), `HILDON_THEME`, `PY` (the ARM Python 3).

## With and without a phone
The Hildon look of the N900 comes from Nokia's theme `beta` ("Digital Nature") and the font Nokia Sans. Both are in the `nokia-binaries` repository of the Maemo SDK, which falls under
Nokia's licence, and the public mirrors do not serve the files. So **without a phone** the emulator draws with a stand-in: a dark theme of the kit (`theme/devkit`: black, white text,
orange selection) and DejaVu Sans, with the real GTK 2.14 / Hildon libraries and layout. That is good for the layout and the logic of your program, not for pixel comparison.
With **your own N900** run `make hildon-overlay DEVICE=root@<address>` once (~100 MB): the theme `beta`, the Nokia fonts and Python 2.5 with PyGTK are copied from it, and the emulator
uses them from then on (`HILDON_THEME=<name>` selects another installed theme). Programs for Python 2.5 with PyGTK (`PY2=1`) need that phone copy, their bindings are not on the mirrors.

## What is where

```
Makefile, mk/common.mk, mk/devkit.mk   the targets above (mk/ is shared with nokia-n900-apps)
.workshop/n900.yaml                    the Workshop: the toolchain action installs everything the scripts need
scripts/maemo-gcc, maemo-compat.h ...  the cross compiler wrapper and compatibility headers for glibc 2.5
scripts/fetch_sysroot.py               the sysroot from the mirrors (maemo.plan9.de, maemo.viniciuspaes.com)
scripts/fetch_python3.py               the ARM Python 3 and hildonlite from our apt repository (SHA-256 checked)
scripts/fetch_overlay.py               the runtime files of the emulator without a phone (locale archive, icons, fontconfig, pango, fonts)
theme/devkit/                          the stand-in GTK theme used when the sysroot has no Nokia theme
scripts/hildon-*.sh, hildon-shell.py   the emulator: virtual screen, window manager, top bar and launcher, D-Bus atrapy for Maemo services
scripts/hildon-stubs/                  replacements of python-osso and conic (they need the Maemo system bus)
scripts/qemu-*, emu-*                  qemu-user helpers and the tests in an emulated phone
apps/quick-notes/                      an example application: Python 3, hildonlite, tests, a screenshot scenario
src/                                   a hello world in C and a proof of the Hildon emulator in Python 3
docs/                                  the documentation
```

## Use in the main repository
[nokia-n900-apps](https://github.com/n900-resurrection/nokia-n900-apps) has this repository as the submodule `devkit/`; its `scripts/…`, `mk/common.mk` and `.workshop/n900.yaml`
are symbolic links into it, so all its application builds keep their paths. The `Makefile` of the main repository includes `devkit/mk/devkit.mk`.

## Licence
MIT, see [LICENSE](LICENSE). The sysroot and the files copied from your phone belong to their owners and are not part of this repository (they are in `.gitignore`).
