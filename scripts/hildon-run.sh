#!/bin/bash
# Run INSIDE the Workshop: start an ARM program (python3 script or any binary) with the real GTK 2.14 / Hildon libraries
# of the Fremantle sysroot under qemu-user, on a virtual X screen of the container (Xvfb, 800x480 like the N900).
#   scripts/hildon-run.sh script.py                 ... run a Python 3 script (the cross-built ARM python3); an ARM binary (ELF) is run directly
#   SHOT=out.png SHOT_AFTER=6 scripts/hildon-run.sh script.py   ... screenshot after 6 s
#   PY2=1 scripts/hildon-run.sh script.py          ... run it with the phone's Python 2.5 + PyGTK + Hildon (like mutt-hildon)
#   VNC=1 scripts/hildon-run.sh script.py           ... also serve the screen over VNC (port 5999 of the container)
#   DESKTOP=1 ... with the window manager and the top bar (default for APP=, see hildon-session.sh)
#   APP=mutt-hildon scripts/hildon-run.sh           ... run an application that has $APPS_DIR/<app>/hildon-run.sh (demo data, own settings; default apps/)
# Needs: make python3 (the ARM interpreter), make hildon-overlay (theme/fonts from the phone), apt: xvfb x11vnc imagemagick.
set -euo pipefail
PROJ="${PROJ:-/project}"
APPS_DIR="${APPS_DIR:-$PROJ/apps}"       # the applications of the developer: <app>/hildon-run.sh describes how the emulator starts one (demo data, settings)
SR="${SYSROOT:-$PROJ/sysroot}"
D="${XDISPLAY:-:99}"
# DESKTOP=1 (the default with APP=): window manager + top bar with the application switcher, launcher, clock, Menu and Back (hildon-session.sh)
if [ "${DESKTOP:-${APP:+1}}" = 1 ]; then
    export HILDON_SHELL=1
    XDISPLAY="$D" FRESH=1 NOSHELL=1 "$PROJ/scripts/hildon-session.sh"
    # the session lives as long as this command: the program runs in the background, the bar in the foreground
    # (closing the program with Back leaves the emulator open, Ctrl-C ends it)
    DESKTOP=0 "$0" "$@" &
    exec env XDISPLAY="$D" FOREGROUND=1 "$PROJ/scripts/hildon-session.sh"
else
    pgrep -x Xvfb >/dev/null || { Xvfb "$D" -screen 0 800x480x24 >/tmp/xvfb.log 2>&1 & sleep 1.5; }
    [ -z "${VNC:-}" ] || pgrep -x x11vnc >/dev/null || x11vnc -display "$D" -rfbport 5999 -forever -nopw -shared -bg -q >/dev/null 2>&1
fi
# private D-Bus bus with the mocked Maemo services (icd, MAFW); programs use it as session and system bus
"$PROJ/scripts/hildon-dbus.sh"
export DBUS_SESSION_BUS_ADDRESS=unix:path=/tmp/hildon-emu-bus DBUS_SYSTEM_BUS_ADDRESS=unix:path=/tmp/hildon-emu-bus
if [ -n "${APP:-}" ]; then
    # apps/<app>/hildon-run.sh may set PY2, HOME, RUN_SCRIPT and prepare data
    [ -f "$APPS_DIR/$APP/hildon-run.sh" ] || { echo "$APPS_DIR/$APP/hildon-run.sh does not exist"; exit 1; }
    # shellcheck disable=SC1090
    . "$APPS_DIR/$APP/hildon-run.sh"
    set -- "${RUN_SCRIPT:?}" "$@"
fi
# The ARM Python 3: PY=<dir> wins; else the cross-built one (build/out/python3-*, nokia-n900-apps), else the one from the repository (make arm-python)
if [ -z "${PY:-}" ]; then
    for c in "$PROJ"/build/out/python3-3.11.*/root/opt/python3 "$SR/opt/python3"; do
        [ -x "$c/bin/python3.11" ] && { PY="$c"; break; }
    done
    : "${PY:?no ARM Python 3 found: make arm-python (downloads it from the apt repository), or build it with make python3 in nokia-n900-apps}"
fi
# LC_ALL=C: the glibc 2.5 of the sysroot cannot read the locale files of the host.
# GTK2_RC_FILES: the theme the phone chooses through xsettings (hildon-desktop is not running here): beta (from a phone, make hildon-overlay DEVICE=...),
# else alpha, else the stand-in theme of the kit (make hildon-overlay without a phone); HILDON_THEME=<name> selects one.
THEME="${HILDON_THEME:-}"
if [ -z "$THEME" ]; then
    for t in beta alpha devkit; do [ -f "$SR/usr/share/themes/$t/gtk-2.0/gtkrc" ] && { THEME=$t; break; }; done
    : "${THEME:?no GTK theme in the sysroot: make hildon-overlay (from a phone with DEVICE=..., or downloaded without one)}"
fi
export DISPLAY="$D" PYTHONHOME="$PY" QEMU_LD_PREFIX="$SR" LC_ALL=C LANG=C \
       GTK2_RC_FILES="/usr/share/themes/$THEME/gtk-2.0/gtkrc"
# sapwood-server: the GTK engine of the Fremantle themes (sapwood) asks this server for the images of the skin; without it buttons, entries and
# sliders are drawn as nothing but their text. The phone runs it from the session; here it is started once per screen (it ends with the session).
SW="$SR/usr/lib/sapwood/sapwood-server"
if [ -x "$SW" ] && ! pgrep -f '[s]apwood-server' >/dev/null; then
    DISPLAY="$D" QEMU_LD_PREFIX="$SR" LC_ALL=C setsid "$SW" >/tmp/sapwood-server.log 2>&1 &
    sleep 1
fi
if [ -n "${SHOT:-}" ]; then
    ( sleep "${SHOT_AFTER:-6}"; import -display "$D" -window root "$SHOT" ) &
fi
if [ -n "${PY2:-}" ]; then
    # hildon-stubs: replacement of python-osso (needs the Maemo system bus); EXTRA_PYTHONPATH: the program under test
    export PYTHONPATH="${EXTRA_PYTHONPATH:+$EXTRA_PYTHONPATH:}$PROJ/scripts/hildon-stubs:/usr/lib/pymodules/python2.5/gtk-2.0:/usr/lib/pymodules/python2.5:/usr/lib/python2.5/site-packages"
    unset PYTHONHOME
    export HILDON_DEVSHELL=1   # buttons Menu/Back + keys F4/Escape (hildon-stubs/sitecustomize.py)
    exec qemu-arm "$PROJ/sysroot/usr/bin/python2.5" "$@"
fi
# an ARM program (an ELF file, for example a GTK program built with scripts/maemo-gcc) is started directly under qemu-user, in the same environment
if [ "$(head -c4 "${1:-/dev/null}" 2>/dev/null | tail -c3)" = ELF ]; then exec qemu-arm "$@"; fi
# hildonlite comes with the interpreter from the repository (make arm-python); a cross-built Python (nokia-n900-apps) has none, so the site-packages of the
# downloaded one are added when they are there
SP="$SR/opt/python3/lib/python3.11/site-packages"
if [ "$PY" != "$SR/opt/python3" ] && [ -d "$SP/hildonlite" ]; then export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$SP"; fi
exec qemu-arm "$PY/bin/python3.11" "$@"
