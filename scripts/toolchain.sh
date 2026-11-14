#!/bin/bash
# Run INSIDE the Workshop (make toolchain): install the armel cross toolchain, qemu-user and everything the scripts of the kit and of the applications use:
#   autoconf automake libtool (autoreconf), gettext (msgfmt), python3-pip, xvfb x11vnc imagemagick x11-utils (the emulator: virtual screen, VNC, screenshots),
#   matchbox-window-manager wmctrl xdotool python3-gi gir1.2-gtk-3.0 xterm (the emulated desktop), rsync, xz/bzip2/patch/curl.
# A script (and not only the action of .workshop/n900.yaml) because `workshop run <workshop> -- toolchain` did not return after the installation had ended;
# `make toolchain` runs this through scripts/ws-exec.sh, which does not hang.
set -euo pipefail
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y build-essential gcc-arm-linux-gnueabi g++-arm-linux-gnueabi binutils-arm-linux-gnueabi file dpkg-dev python3 python3-pip git ninja-build meson make pkg-config qemu-user qemu-user-static autoconf automake libtool gettext patch xz-utils bzip2 unzip curl ca-certificates rsync perl bison xvfb x11vnc x11-utils imagemagick matchbox-window-manager wmctrl xdotool python3-gi python3-gi-cairo gir1.2-gtk-3.0 xterm
