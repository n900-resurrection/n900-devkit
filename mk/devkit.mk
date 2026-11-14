# The workshop, the cross toolchain, the sysroot and the emulated Fremantle desktop: the part of the Makefile that belongs to the development kit
# (n900-devkit). Included by the Makefile of the kit itself and by the main repository (nokia-n900-apps, where the kit is the folder devkit/).
# Needs mk/common.mk (settings, INSIDE, colours, help) included first. Conventions as in mk/common.mk: a description variable named like the target.

DEVKIT_TARGETS := up down status enter toolchain sysroot hello emu-test emu-shots locale-overlay hildon-overlay emulator emulator-stop hildon-run
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
	$(WSRUN) toolchain

SYSROOT := Download the Fremantle SDK sysroot into ./sysroot
sysroot:
	$(WSRUN) sysroot

HELLO := Build and run hello.c (qemu-user, glibc 2.5)
hello:
	$(WSRUN) cpp-hello

EMU-TEST := Run apps/<app>/test.sh in the emulated phone (chroot under qemu-user, no phone): make emu-test APP="jq tmux" (default: all apps with test.sh); RESET=1 builds the root again
emu-test:
	$(INSIDE) bash -c '$(if $(RESET),/project/scripts/emu-root.sh --reset &&) /project/scripts/emu-test.sh $(if $(APP),$(APP),$(notdir $(patsubst %/,%,$(dir $(wildcard apps/*/test.sh)))))'

EMU-SHOTS := Take the screenshots of an application in the emulated desktop from the timeline apps/<app>/shots.txt into build/shots/<app>/ (APP="mutt-hildon"; COMPARE=dir compares with older images)
emu-shots:
	$(INSIDE) /project/scripts/emu-shots.sh $(if $(COMPARE),--compare $(COMPARE)) $(if $(APP),$(APP),$(notdir $(patsubst %/,%,$(dir $(wildcard apps/*/shots.txt)))))

LOCALE-OVERLAY := Copy the locale archive (UTF-8 locales, glibc 2.5) from the phone into ./sysroot (once; tmux and other programs need it under qemu-user)
locale-overlay:
	DEVICE=$(DEVICE) scripts/locale-overlay.sh

HILDON-OVERLAY := Copy the Hildon theme, fonts and icons from the phone into ./sysroot (once; for hildon-run)
hildon-overlay:
	DEVICE=$(DEVICE) scripts/hildon-overlay.sh

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
ifneq ($(and $(filter apps/%,$(SCRIPT)),$(wildcard apps/$(SCRIPTAPP)/hildon-run.sh)),)
APP := $(SCRIPTAPP)
endif
endif
hildon-run:
	$(INSIDE) env SHOT=$(SHOT) VNC=$(VNC) PY2=$(PY2) APP=$(APP) HILDON_DEVSHELL_SCRIPT=$(DEVSHELL_SCRIPT) HILDON_DEVSHELL_DEBUG=$(DEVSHELL_DEBUG) /project/scripts/hildon-run.sh $(if $(APP),,/project/$(SCRIPT))
