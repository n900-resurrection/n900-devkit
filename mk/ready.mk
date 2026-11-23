# The environment as dependencies: what has to exist before something can be built or run. Included by common.mk, so every Makefile
# (the root one and apps/<app>/Makefile) can name them as order-only prerequisites (`build: | ws-ready`).
#
#   ws-ready    enough to BUILD:   the workshop is launched -> the toolchain is installed;  the sysroot is downloaded
#   emu-ready   enough to RUN in the emulator (emu-test, hildon-run, emulator, qemu-smoke): ws-ready + arm-python + hildon-overlay + locale-overlay
#   init        = emu-ready, for those who want the whole environment at once
#
# The first `make <app>` on a clean clone therefore creates the workshop and downloads what it needs (and says so); a developer only
# installs the host tools (snap lxd, snap workshop, git submodules) and, if wanted, sets DEVICE in .env (the overlay then comes from the phone).
#
# Stamps live in sysroot/.stamps: the stamp of the sysroot goes away with the sysroot, and `make clean` (which removes build/) does not
# make the environment be downloaded again. The workshop itself is not a file: it is checked on every run (ws-up), and the stamp changes
# only when the container was created, which is the only case when the toolchain has to be installed again.

STAMPS := $(ROOT)/sysroot/.stamps
.PHONY: ws-ready emu-ready init ws-force

WS-READY := Create and prepare what is needed to build: the workshop, the toolchain, the sysroot (only what is missing; the others do this by themselves)
ws-ready: $(STAMPS)/sysroot

EMU-READY := Prepare what is needed to run in the emulator: ws-ready, ARM Python, the overlays (only what is missing)
emu-ready: ws-ready $(STAMPS)/arm-python $(STAMPS)/hildon-overlay $(STAMPS)/locale-overlay

INIT := Prepare the whole environment from a clean clone: workshop, toolchain, sysroot, ARM Python, overlays (only what is missing)
init: emu-ready

ws-force:

# The container: checked every time (it can be removed behind our back), the stamp is renewed only after it was created.
# A stopped one is started again (the toolchain in it stays).
$(STAMPS)/ws-up: ws-force
	@command -v workshop >/dev/null || { printf '$(RED)The command workshop is missing. Install it (once):$(RESET)\n  sudo snap install --channel=6/stable lxd && lxd init\n  sudo snap install --classic workshop\n'; exit 1; }
	@state=$$($(WORKSHOP) list 2>/dev/null | awk -v w="$(WS)" '$$1 == w {print $$2}'); \
	if [ -z "$$state" ]; then \
	    printf '$(BOLD)== workshop $(WS): creating (first run)$(RESET)\n'; \
	    $(WORKSHOP) launch $(WS) || exit 1; mkdir -p $(STAMPS); touch $@; \
	elif [ "$$state" = Off ]; then \
	    printf '$(BOLD)== workshop $(WS): starting$(RESET)\n'; \
	    $(WORKSHOP) launch $(WS) || exit 1; [ -e $@ ] || { mkdir -p $(STAMPS); touch $@; }; \
	elif [ ! -e $@ ]; then mkdir -p $(STAMPS); touch $@; fi

# Every step that changes the container waits for the container only (order-only for the files on the host: they stay valid after it is recreated).
$(STAMPS)/toolchain: $(STAMPS)/ws-up $(ROOT)/scripts/toolchain.sh
	@printf '$(BOLD)== toolchain: installing in the workshop (first run)$(RESET)\n'
	$(INSIDE) bash /project/scripts/toolchain.sh
	@touch $@

$(STAMPS)/sysroot: $(ROOT)/scripts/fetch_sysroot.py | $(STAMPS)/toolchain
	@printf '$(BOLD)== sysroot: downloading the Fremantle SDK (first run, a few hundred MB)$(RESET)\n'
	$(WSRUN) sysroot
	@touch $@

$(STAMPS)/arm-python: | $(STAMPS)/sysroot
	@printf '$(BOLD)== arm-python: downloading Python 3.11 and hildonlite for the emulator$(RESET)\n'
	$(WSRUN) arm-python
	@touch $@

$(STAMPS)/hildon-overlay: | $(STAMPS)/sysroot
	@printf '$(BOLD)== hildon-overlay: runtime files of the emulator$(RESET)\n'
	@if [ -n "$(DEVICE)" ]; then DEVICE=$(DEVICE) $(ROOT)/scripts/hildon-overlay.sh; else $(WSRUN) overlay; fi
	@touch $@

$(STAMPS)/locale-overlay: | $(STAMPS)/sysroot
	@printf '$(BOLD)== locale-overlay: UTF-8 locales for the emulator$(RESET)\n'
	@if [ -n "$(DEVICE)" ]; then DEVICE=$(DEVICE) $(ROOT)/scripts/locale-overlay.sh; else $(WSRUN) overlay-locale; fi
	@touch $@
