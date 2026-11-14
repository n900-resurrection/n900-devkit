# n900-devkit

Everything you need to **write and try an application for the Nokia N900 (Maemo 5, armel, glibc 2.5) on a PC**, without cloning the whole
[nokia-n900-apps](https://github.com/n900-resurrection/nokia-n900-apps) repository:

- a **Workshop** (a container, Ubuntu 24.04) with the armel cross toolchain (`scripts/maemo-gcc`) and `qemu-user`,
- the **Fremantle sysroot** of the Maemo 5 SDK (`make sysroot`),
- an **emulated Hildon desktop**: your GTK2/Hildon program (Python 3 with [hildonlite](https://github.com/n900-resurrection/hildonlite), Python 2.5 with PyGTK, or a C program)
  runs under `qemu-user` against the real GTK 2.14 / Hildon libraries on a virtual 800x480 screen, with a top bar, task switcher and launcher like the N900's,
- test scripts that run in an emulated phone (`make emu-test`).

Nothing from Nokia is stored in this repository: the theme, fonts and icons of the phone are copied **from your own N900** once (`make hildon-overlay`),
the SDK sysroot comes from the community mirrors (`scripts/fetch_sysroot.py`).

## Quick start

You need Ubuntu (or another Linux) with [Workshop](https://snapcraft.io/workshop) and LXD (`sudo snap install --channel=6/stable lxd`, `sudo snap install --classic workshop`, `lxd init`).

```sh
git clone https://github.com/n900-resurrection/n900-devkit.git
cd n900-devkit
make up toolchain sysroot            # the container, the toolchain, the sysroot (once, a few hundred MB)
make hello                           # build and run a C program for the N900 under qemu-user
make arm-python                      # Python 3.11 and hildonlite for the N900, from the apt repository of the project (no cross-build)
make hildon-overlay DEVICE=root@192.168.1.50    # theme, fonts, icons and Python 2.5 from your phone (once, ~100 MB)
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
| `hildon-overlay` | copy the Hildon theme, fonts, icons and Python 2.5 from the phone into the sysroot |
| `locale-overlay` | copy the locale archive from the phone (programs such as tmux need it under qemu-user) |
| `hildon-run` | show a GTK2/Hildon program: `SCRIPT=file.py`, `APP=<app>` (an application with `apps/<app>/hildon-run.sh`), `SHOT=file.png`, `VNC=1`, `PY2=1` |
| `emulator`, `emulator-stop` | start/stop the emulated desktop (top bar, launcher, task switching) |
| `emu-test`, `emu-shots` | run the tests of applications in an emulated phone, take screenshots from a timeline |

## What is where

```
Makefile, mk/common.mk, mk/devkit.mk   the targets above (mk/ is shared with nokia-n900-apps)
.workshop/n900.yaml                    the Workshop: the toolchain action installs everything the scripts need
scripts/maemo-gcc, maemo-compat.h ...  the cross compiler wrapper and compatibility headers for glibc 2.5
scripts/fetch_sysroot.py               the sysroot from the mirrors (maemo.plan9.de, maemo.viniciuspaes.com)
scripts/fetch_python3.py               the ARM Python 3 and hildonlite from our apt repository (SHA-256 checked)
scripts/hildon-*.sh, hildon-shell.py   the emulator: virtual screen, window manager, top bar and launcher, D-Bus atrapy for Maemo services
scripts/hildon-stubs/                  replacements of python-osso and conic (they need the Maemo system bus)
scripts/qemu-*, emu-*                  qemu-user helpers and the tests in an emulated phone
src/                                   a hello world in C and a proof of the Hildon emulator in Python 3
```

## Use in the main repository
[nokia-n900-apps](https://github.com/n900-resurrection/nokia-n900-apps) has this repository as the submodule `devkit/`; its `scripts/…`, `mk/common.mk` and `.workshop/n900.yaml`
are symbolic links into it, so all its application builds keep their paths. The `Makefile` of the main repository includes `devkit/mk/devkit.mk`.

## Licence
MIT, see [LICENSE](LICENSE). The sysroot and the files copied from your phone belong to their owners and are not part of this repository (they are in `.gitignore`).
