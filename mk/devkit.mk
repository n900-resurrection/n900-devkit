# The workshop, the cross toolchain, the sysroot and the emulated Fremantle desktop: the part of the Makefile that belongs to the development kit
# (n900-devkit). Included by the Makefile of the kit itself and by the main repository (nokia-n900-apps, where the kit is the folder devkit/).
# Needs mk/common.mk (settings, INSIDE, colours, help) included first. Conventions as in mk/common.mk: a description variable named like the target.

# APPS_DIR: the applications of the developer, relative to the project: <app>/hildon-run.sh (how the emulator starts one), test.sh, shots.txt
APPS_DIR ?= apps

DEVKIT_TARGETS := up down status enter toolchain sysroot arm-python hello emu-test emu-shots locale-overlay hildon-overlay hildon-overlay-download emulator emulator-stop hildon-run clean clean-all
.PHONY: $(DEVKIT_TARGETS)

UP := Create and start the workshop (first run)
up:
	$(WORKSHOP) launch $(WS)

DOWN := Stop the workshop
down:
	$(WORKSHOP) stop $(WS)

STATUS := Show the workshop status
status:
	$(WORKSHOP) list

ENTER := Open an interactive shell inside the workshop
enter:
	$(WORKSHOP) shell $(WS)

TOOLCHAIN := Install the armel cross toolchain and qemu-user
toolchain:
	$(INSIDE) bash /project/scripts/toolchain.sh

SYSROOT := Download the Fremantle SDK sysroot into ./sysroot
sysroot:
	$(WSRUN) sysroot

ARM-PYTHON := Download Python 3.11 and hildonlite for the N900 (packages of the project apt repository) into ./sysroot/opt/python3, for hildon-run (no cross-build)
arm-python:
	$(WSRUN) arm-python

HELLO := Build and run hello.c (qemu-user, glibc 2.5)
hello:
	$(WSRUN) cpp-hello

EMU-TEST := Run apps/<app>/test.sh in the emulated phone (chroot under qemu-user, no phone): make emu-test APP="jq tmux" (default: all apps with test.sh); RESET=1 builds the root again
emu-test:
	$(INSIDE) env APPS_DIR=/project/$(APPS_DIR) bash -c '$(if $(RESET),/project/scripts/emu-root.sh --reset &&) /project/scripts/emu-test.sh $(if $(APP),$(APP),$(notdir $(patsubst %/,%,$(dir $(wildcard $(APPS_DIR)/*/test.sh)))))'

EMU-SHOTS := Take the screenshots of an application in the emulated desktop from the timeline apps/<app>/shots.txt into build/shots/<app>/ (APP="mutt-hildon"; COMPARE=dir compares with older images)
emu-shots:
	$(INSIDE) env APPS_DIR=/project/$(APPS_DIR) /project/scripts/emu-shots.sh $(if $(COMPARE),--compare $(COMPARE)) $(if $(APP),$(APP),$(notdir $(patsubst %/,%,$(dir $(wildcard $(APPS_DIR)/*/shots.txt)))))

LOCALE-OVERLAY := The locale archive (UTF-8 locales, glibc 2.5) into ./sysroot (once; tmux and other programs need it under qemu-user): from your phone when DEVICE is set, otherwise downloaded (package posix-locales)
locale-overlay:
	@if [ -n "$(DEVICE)" ]; then DEVICE=$(DEVICE) scripts/locale-overlay.sh; else $(WSRUN) overlay-locale; fi

HILDON-OVERLAY := The runtime files of the Hildon emulator into ./sysroot (once): from your phone when DEVICE=user@address is set (the exact look: Nokia theme, fonts, Python 2.5), otherwise downloaded (hildon-overlay-download)
hildon-overlay:
	@if [ -n "$(DEVICE)" ]; then DEVICE=$(DEVICE) scripts/hildon-overlay.sh; else $(MAKE) --no-print-directory hildon-overlay-download; fi

HILDON-OVERLAY-DOWNLOAD := The runtime files of the emulator without a phone: icons, fontconfig, pango, GTK engine from the Maemo mirrors, DejaVu fonts of the host and a stand-in theme (close to the phone, not the same look)
hildon-overlay-download:
	$(WSRUN) overlay

EMULATOR := Start the emulated Fremantle desktop (top bar, launcher, task switching): make emulator (VNC on port 5999 of the Workshop, address is printed)
emulator:
	$(INSIDE) env VNC=$(or $(VNC),1) FRESH=1 FOREGROUND=1 /project/scripts/hildon-session.sh

EMULATOR-STOP := End a running emulator session (screen, VNC, window manager, bar, programs)
emulator-stop:
	$(INSIDE) env STOP=1 /project/scripts/hildon-session.sh

HILDON-RUN := Show a GTK2/Hildon program on a virtual 800x480 screen: make hildon-run [APP=mutt-hildon | SCRIPT=src/python3/hildon/proof.py] [SHOT=build/shot.png] [VNC=1] [PY2=1 for Python 2.5]
SCRIPT ?= src/python3/hildon/proof.py
# SCRIPT=apps/<app>/... of an application that has apps/<app>/hildon-run.sh means APP=<app> (it needs the demo home)
ifeq ($(APP),)
SCRIPTAPP := $(word 2,$(subst /, ,$(SCRIPT)))
ifneq ($(and $(filter $(APPS_DIR)/%,$(SCRIPT)),$(wildcard $(APPS_DIR)/$(SCRIPTAPP)/hildon-run.sh)),)
APP := $(SCRIPTAPP)
endif
endif
hildon-run:
	$(INSIDE) env APPS_DIR=/project/$(APPS_DIR) SHOT=$(SHOT) VNC=$(VNC) PY2=$(PY2) APP=$(APP) HILDON_DEVSHELL_SCRIPT=$(DEVSHELL_SCRIPT) HILDON_DEVSHELL_DEBUG=$(DEVSHELL_DEBUG) /project/scripts/hildon-run.sh $(if $(APP),,/project/$(SCRIPT))

CLEAN := Remove the build output (./build: the emulator root, screenshots, programs built by the scripts); the sysroot and the workshop stay
clean:
	rm -rf build

CLEAN-ALL := Back to nothing: remove ./build, ./sysroot, ./downloads and the workshop container (the definition stays), so that make up toolchain sysroot starts from scratch. Asks first, YES=1 skips the question
clean-all:
	@if [ -z "$(YES)" ]; then printf '$(YELLOW)This removes build/, sysroot/, downloads/ and the workshop %s (a big sysroot and toolchain take a long time to get again). Continue? [y/N] $(RESET)' '$(WS)'; read a; [ "$$a" = y ] || { echo aborted; exit 1; }; fi
	-$(WORKSHOP) remove $(WS)
	rm -rf build sysroot downloads
	@printf '$(GREEN)Clean. Start again with: make up toolchain sysroot arm-python hildon-overlay locale-overlay$(RESET)\n'
