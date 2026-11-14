# The emulated Hildon desktop

The emulator runs GTK 2.14 / Hildon 2.2 programs of the N900 on a PC: the ARM programs run under **qemu-user** against the real libraries of the Maemo sysroot, the picture goes to a virtual
**800x480 screen** (Xvfb), and a window manager with a top bar makes it behave like the N900 (applications get 800x424 under a 56 px bar).
It is made for developing applications: the look of the widgets and the logic of the program are the same as on the phone; speed is not (qemu is slow, a Python start takes seconds).

## Run a program
```sh
make hildon-run SCRIPT=file.py [SHOT=build/shot.png] [VNC=1]      # one program on the virtual screen, screenshot after 6 s (SHOT_AFTER)
make hildon-run APP=<app> [SHOT=...]                              # an application of the developer in the desktop (top bar, switcher): APPS_DIR/<app>/hildon-run.sh
make emulator                                                     # the empty desktop with the launcher; VNC on port 5999 of the container
make emulator-stop                                                # end a session that was left behind
```
`SCRIPT` is a Python 3 file (the interpreter from `make arm-python`, or a cross-built one); `PY2=1` uses the phone's Python 2.5 with PyGTK (needs `make hildon-overlay DEVICE=...`).
`VNC=1` serves the screen over VNC (`x11vnc`, port 5999 of the container, no password); the address is printed, or `workshop -p . exec n900 -- hostname -I`. Connect with `remmina` or `vncviewer`;
a mouse click is a tap, so touch interaction can be tried. The screenshot is written under `/project`, which is the project folder on the host.

## Your application: `apps/<app>/hildon-run.sh`
An application is known to the launcher and to `make hildon-run APP=<app>` when `apps/<app>/hildon-run.sh` exists (the directory is `APPS_DIR`, default `apps/`). The file is sourced by
`scripts/hildon-run.sh` and sets what is needed; the first lines may carry the name for the launcher:
```sh
# Name: Quick notes
RUN_SCRIPT="$APPS_DIR/quick-notes/quick-notes"       # the program to start (required)
export QUICKNOTES_FILE=/tmp/quick-notes-demo.json    # settings of the program; demo data in /tmp, never your real data
PY2=1                                                # optional: Python 2.5 with PyGTK instead of Python 3
```
`apps/quick-notes` is a complete example ([python-gui.md](python-gui.md)). `apps/<app>/icons/48.png` is the icon in the launcher.

## The desktop (`scripts/hildon-session.sh`, `scripts/hildon-shell.py`)
- **Screen and window manager:** `Xvfb` 800x480 and `matchbox-window-manager`; the wallpaper is `background-1.png` copied from a phone by `make hildon-overlay DEVICE=...` (otherwise black; `HILDON_BG=file.png`).
- **The top bar** (`hildon-shell.py`, host GTK 3) follows the screenshots of the phone: `[windows] | clock and battery | application title v | [back]`.
  The orange button on the left cycles: current application, the **switcher** (a card per running application: title, X to close it, the picture of the window), the **launcher** (all
  applications, five icons per row), current application. The title is the **Menu** button of the active window, the arrow on the right is **Back** (closes the active window; in the switcher it
  leaves the switcher). A tap on the clock opens a simplified status panel. Closing the last window leaves the emulator running; Ctrl-C ends the session.
- **Menu:** `HildonAppMenu.popup()` shows nothing without `hildon-desktop`, so the items are shown in a window of our own and a tap calls the original button. Keys: F4 = Menu, Escape = Back,
  like on the N900. The popup is closed by choosing an item (not by Escape or a tap outside).
- **Applications found automatically:** the launcher lists the `apps/<app>/hildon-run.sh` of the developer and every `.deb` in `build/deb/` (`DEB_DIR`) that has a
  `/usr/share/applications/hildon/*.desktop`; such a package is unpacked into the sysroot on its first start (like an installation) and runs as on the phone. ARM programs run through
  `binfmt_misc` (registered with sudo by the session script), `sysroot/opt` is bind-mounted on `/opt` (qemu-user does not translate the path of `execve`; `emulator-stop` removes the mount),
  `osso-xterm -e CMD` entries open in a host xterm.
- **D-Bus mocks:** `scripts/hildon-dbus.sh` starts a private bus (`/tmp/hildon-emu-bus`, used as session and system bus) and `scripts/hildon-dbus-mocks.py` registers the Maemo services on it:
  `com.nokia.icd` (the connection daemon) and the MAFW media renderer (an idle player). One class per service in that file; the calls are logged to `/tmp/hildon-dbus-mocks.log`.
- **Python 2.5 helpers:** `scripts/hildon-stubs/` replaces `python-osso` and `conic` (they need the Maemo system bus): the network is always "WLAN", the Menu/Back buttons and the keys
  F4/Escape come from `sitecustomize.py` (`HILDON_DEVSHELL=1`). `DEVSHELL_DEBUG=1` logs to `/tmp/hildon-devshell.log` in the container.

## Theme and fonts
The theme the program uses is chosen in this order: `HILDON_THEME=<name>` if set, else **`beta`** (the Nokia theme, copied from a phone), else `alpha`, else the stand-in **`devkit`**
(`theme/devkit`: dark, white text, orange selection, plain GTK drawing; installed by `make hildon-overlay` without a phone). Fonts: the Nokia fonts from a phone, else DejaVu Sans from the host.
`LC_ALL=C` is the default (the glibc 2.5 of the sysroot cannot read the locale files of the host); `make locale-overlay` adds the glibc 2.5 locale archive (UTF-8 locales), which programs such as tmux need.

## Tests and screenshots
- **Several screenshots in a row:** `make emu-shots APP=<app>` follows a timeline `apps/<app>/shots.txt`, one line per step `SECONDS ACTION [ARGS]` counted from the start of the program:
  `shot NAME` (to `build/shots/<app>/NAME.png`), `click X Y`, `key NAME` (xdotool; F4 = Menu, Escape = Back), `type TEXT`. The program starts fresh for every run, so the images are
  reproducible; `build/shots/<app>/contact-sheet.png` shows all of them (ImageMagick montage), `COMPARE=dir` compares each image with an older set and prints the number of pixels that differ.
- **Test suites in an emulated phone:** `make emu-test APP="app1 app2"` runs `apps/<app>/test.sh` in a chroot under qemu-user (`build/emu-root`, a few hundred MB, built on the first run;
  `RESET=1` builds it again) with a stand-in for `dpkg`, like on the phone. These are shell tests of the kind used by nokia-n900-apps (`tests/lib.sh` is theirs).
  `scripts/qemu-smoke.sh` runs quick smoke tests of built programs.
- **Phone-like limits:** `scripts/qemu-n900 PROGRAM` starts a program as the N900 would see it: kernel 2.6.28, one CPU, a private 1 MB `/tmp`.

## What it cannot do
- **`hildon-desktop` does not run on a PC.** It draws through clutter and OpenGL ES 2 on the PowerVR graphics (`libIMGegl`), which have nothing to run on under qemu-user. So there is no real status
  area, task switcher, widgets or Maemo on-screen keyboard (use the keyboard of the PC). The only complete emulation was the old x86 Maemo SDK rootstrap, which is not downloadable any more.
- Speed is emulated; kinetic scrolling (`PannableArea`) can only be tried roughly.
- The exact Nokia look needs a phone (see [getting-started.md](getting-started.md)); Python 2.5 programs with PyGTK (`PY2=1`) need the bindings from a phone as well.
- Services that are not mocked (the connection daemon `icd` and the media renderer are) end an application with an error: add a class to `hildon-dbus-mocks.py`.
- Hardware: sensors, the camera, the real keyboard.
