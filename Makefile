# n900-devkit: develop and test applications for the Nokia N900 (Maemo 5) on a PC: a Workshop (container) with the armel cross toolchain and qemu-user,
# the Fremantle sysroot, and the emulated Hildon desktop. See README.md. The same makefile parts are used by the main repository (nokia-n900-apps).

include mk/common.mk
include mk/devkit.mk

TARGETS := help $(DEVKIT_TARGETS)
.PHONY: $(TARGETS)
