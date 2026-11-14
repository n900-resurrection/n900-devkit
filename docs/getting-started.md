# Getting started

n900-devkit gives you, on a PC, everything to write and try software for the Nokia N900 (Maemo 5, armel, glibc 2.5, GTK 2.14 / Hildon 2.2):
a container with the cross toolchain, the Fremantle sysroot, and an emulated Hildon desktop. No phone is needed.

## What you need
- A Linux PC with **LXD** and **Workshop** (Canonical's tool for project containers):
  ```sh
  sudo snap install --channel=6/stable lxd && sudo lxd init      # defaults are fine
  sudo snap install --classic workshop
  ```
- About 2 GB of disk for the container, the sysroot and the downloads, and an internet connection (the mirrors of Maemo and the apt repository of the project).
- On the host: `make`, `git`, `python3`. Everything else is installed inside the container.
- If Docker runs on the same host, its `FORWARD DROP` rule can block the network of the container (`workshopbr0`); allow it in the `DOCKER-USER` chain.

## Quick start
```sh
git clone https://github.com/n900-resurrection/n900-devkit.git
cd n900-devkit
make up                # creates the container "n900" (about 10 s)
make toolchain         # the armel cross compiler, qemu-user, Xvfb, matchbox ... (apt in the container, a few minutes)
make sysroot           # the Fremantle SDK sysroot from the Maemo mirrors (about 110 packages, ~90 MB)
make arm-python        # Python 3.11 and hildonlite for the N900 from the apt repository of the project
make hildon-overlay    # icons, fontconfig, pango, GTK engine, fonts and the stand-in theme (downloaded)
make locale-overlay    # the glibc 2.5 locale archive (UTF-8 locales)
make hello             # build a C program for the N900 and run it under qemu-user
make hildon-run SCRIPT=src/python3/hildon/proof.py SHOT=build/shot.png    # a Python 3 Hildon window, screenshot after 6 s
make emulator          # the emulated desktop (top bar, launcher), VNC on port 5999 of the container
```
On a recent PC the whole sequence takes a few minutes; `make` without arguments lists all targets. The screenshot lands in `build/` of the project
(`/project` in the container is the project folder on the host).

## With and without a phone
The look of the N900 (the Nokia theme "Digital Nature", the font Nokia Sans) belongs to Nokia and is not downloadable from the public mirrors. Without a phone the emulator
draws with real GTK 2.14 / Hildon libraries but a stand-in theme (`theme/devkit`) and DejaVu Sans: good for layout and logic. If you have an N900 with ssh access, run
`make hildon-overlay DEVICE=root@<address>` once (~100 MB): the theme `beta`, the Nokia fonts and Python 2.5 with PyGTK are copied from it and used from then on.
Details in [emulator.md](emulator.md).

## What to read next
- [python-gui.md](python-gui.md): write a GUI application in Python 3 (hildonlite) and try it in the emulator, with a worked example (`apps/quick-notes`).
- [emulator.md](emulator.md): how the emulated desktop works, what it can and cannot do, tests and screenshots.
- [cross-compile.md](cross-compile.md): building C programs for Maemo 5, the sysroot, the compiler wrapper.

## Starting over
`make clean` removes `build/`. `make clean-all` removes `build/`, `sysroot/`, `downloads/` and the container (it asks first; `YES=1` skips the question), so `make up` starts from scratch.
This is how the kit itself is tested: a fresh clone, then the quick start above.

## Troubleshooting
- **`workshop run ... -- <action>` or `workshop exec` does not return** after the command inside has finished (seen after long installations and builds). `make toolchain` and the targets that run
  commands in the container go through `scripts/ws-exec.sh`: the command writes its exit code to `build/.wsrc.<pid>`, the client is killed when that file exists and it is still there after a
  few seconds, and the whole run is limited by `WS_TIMEOUT` (default 7200 s). A client left from an older run: `pkill -f 'workshop -p .* exec'`.
- **Programs draw empty boxes instead of text:** the pango module list is missing; `make hildon-overlay` makes it (`pango-querymodules` under qemu-user).
- **`no ARM Python 3 found`:** `make arm-python`.
- **`no GTK theme in the sysroot`:** `make hildon-overlay` (with or without `DEVICE`).
