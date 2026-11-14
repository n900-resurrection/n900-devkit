# Cross-compiling for Maemo 5

The N900 runs Maemo 5 (Fremantle): a Debian-like system with **glibc 2.5**, kernel 2.6.28, GTK 2.14 and Hildon 2.2, on an ARM Cortex-A8 (armel, soft-float ABI with NEON available).
The toolchain of the kit is the **gcc 13 cross compiler of Ubuntu 24.04** (`arm-linux-gnueabi-gcc`) pointed at a **sysroot of the Maemo 5 SDK**, so the programs link against glibc 2.5.

## The sysroot
`scripts/fetch_sysroot.py` (standard library of Python only) builds `./sysroot` from the Maemo mirrors (`make sysroot`):
- it reads the `Packages` index of the Fremantle SDK from `maemo.plan9.de` (a snapshot of `repository.maemo.org` from 2017; `maemo.viniciuspaes.com` is the second source for the index),
- takes the newest version of each requested package and resolves its `Depends`,
- downloads only the needed `.deb` files (one at a time, 0.3 s apart, MD5 checked) and unpacks them with `dpkg-deb -x`,
- rewrites absolute symbolic links as relative ones (qemu-user resolves absolute links on the host, the linker would not find `libm.so`).

```sh
python3 scripts/fetch_sysroot.py --dry-run             # the plan (the default set: -dev packages of glibc, ncurses, OpenSSL, GTK, Hildon, SDL, readline ...)
python3 scripts/fetch_sysroot.py libncursesw5-dev      # other packages (inside the container: make enter)
python3 scripts/fetch_sysroot.py --list ncurses        # search the index
```
Versions in the SDK:

| Library | Version |
|---|---|
| glibc | 2.5.1 (eglibc) |
| GCC / libstdc++6 | 4.2.1 |
| ncurses, ncursesw | 5.7+20081213 |
| zlib | 1.2.3 |
| OpenSSL | 0.9.8n (TLS 1.0 only; newer TLS needs a program with its own library) |
| GTK2 / glib | 2.14.7 / 2.20.3 |
| Hildon | 2.2.3 |
| SDL | 1.2.13 |
| readline | 5.2 |

## The compiler wrapper `scripts/maemo-gcc`
A plain `arm-linux-gnueabi-gcc --sysroot=...` does not work: the Ubuntu compiler finds its own libc (glibc 2.39) in `/usr/arm-linux-gnueabi/lib` before the sysroot, so a program asks for symbols
such as `GLIBC_2.34` that Maemo 5 does not have, and the BFD linker 2.42 fails an assertion on objects of glibc 2.5. The wrapper forces `-B`/`-L` and `-nostdinc -isystem` onto the sysroot and uses
the gold linker. Two headers smooth over what glibc 2.5 lacks: `scripts/maemo-compat.h` (for example `O_CLOEXEC`, which the kernel 2.6.28 supports) and `scripts/maemo-endian.h` (the byte-order helpers `htobe32`, `letoh32` ... that came with glibc 2.9). Pull them in with `-include` and do not include anything from them.

```sh
make hello          # builds src/c/hello/hello.c and runs it: "Hello from Maemo 5 (armel, glibc 2.5)"
```
The result is an `ELF 32-bit LSB executable, ARM, EABI5` with the interpreter `/lib/ld-linux.so.3`, the highest symbol version is `GLIBC_2.4`.

## Rules of thumb
- **Always compile with the wrapper** (or with `--sysroot=/project/sysroot`): `libc.so` is a linker script with absolute paths.
- Check what a binary needs: `arm-linux-gnueabi-objdump -T program | grep GLIBC`. Simple C code needs only `GLIBC_2.4`; threads, `stat` and C++ may need newer symbols.
- The ABI is armel (`-march=armv7-a -mfpu=neon -mfloat-abi=softfp`). Static linking (`-static`) is the easy way to a program that runs on any firmware.
- C++: the wrapper is for C. For C++ link libstdc++ statically (`-static-libstdc++ -static-libgcc`); the headers of libstdc++ 4.2 are old.
- `qemu-arm -L sysroot program` only proves that the program links and starts; it says nothing about the 2.6.28 kernel or the hardware. Test on a phone when you can.
- `sysroot/` and `downloads/` are in `.gitignore` and can be recreated with `make sysroot`.

## Running what you built
Inside the container: `qemu-arm -L /project/sysroot build/hello`. For Hildon (GTK2) programs see [emulator.md](emulator.md); for Python programs [python-gui.md](python-gui.md).
`scripts/qemu-n900 PROGRAM...` starts a program with phone-like limits (the kernel version 2.6.28 as seen by the program, one CPU, a private 1 MB `/tmp`).
