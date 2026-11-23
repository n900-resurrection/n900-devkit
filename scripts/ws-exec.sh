#!/bin/bash
# Run a command in the Workshop and do not hang when the `workshop exec` client does not return.
# Usage: scripts/ws-exec.sh ROOT WORKSHOP-NAME COMMAND [ARG...]
#
# Problem: after long commands (a build of GnuTLS, libstrophe...) the client sometimes keeps running although the command
# inside has finished; a `make` waiting for it never goes on and the processes pile up on the host.
# The command writes its exit code into a file inside the project (build/.wsrc.<pid>, the project is /project in the Workshop).
# When the file appears and the client is still there after a grace period, the client is killed and the code is used.
# Besides, the whole run is limited by WS_TIMEOUT seconds (default 7200; 124 = exceeded, the client gets TERM, then KILL).
set -u
ROOT=$1; WS=$2; shift 2
TMO=${WS_TIMEOUT:-7200}; GRACE=${WS_GRACE:-5}
# A workshop belongs to a project folder: a clone, or the folder devkit/ of another repository, has its own and starts with none ("Off").
state=$(workshop -p "$ROOT" list 2>/dev/null | awk -v w="$WS" '$1 == w {print $2}')
if [ -z "$state" ] || [ "$state" = Off ]; then
    echo "ws-exec: the workshop $WS of the project $ROOT is not launched. Run: make ws-ready   (the emulator also needs: make emu-ready)" >&2
    echo "         (a project folder has its own workshop; to use the one of another folder, run make there)" >&2
    exit 1
fi
mkdir -p "$ROOT/build"
RCF="$ROOT/build/.wsrc.$$"
rm -f "$RCF"
trap 'rm -f "$RCF"' EXIT

workshop -p "$ROOT" exec "$WS" -- bash -c '"$@"; rc=$?; echo $rc > "/project/build/.wsrc.$0"; exit $rc' "$$" "$@" <&0 &
CPID=$!
start=$SECONDS; seen=
while kill -0 "$CPID" 2>/dev/null; do
    if [ -s "$RCF" ]; then
        [ -n "$seen" ] || seen=$SECONDS
        if [ $((SECONDS - seen)) -ge "$GRACE" ]; then
            echo "ws-exec: the command finished but 'workshop exec' did not return, killing the client" >&2
            kill -TERM "$CPID" 2>/dev/null; sleep 2; kill -KILL "$CPID" 2>/dev/null
            break
        fi
    fi
    if [ $((SECONDS - start)) -ge "$TMO" ]; then
        echo "ws-exec: timeout after ${TMO} s" >&2
        kill -TERM "$CPID" 2>/dev/null; sleep 5; kill -KILL "$CPID" 2>/dev/null
        wait "$CPID" 2>/dev/null
        exit 124
    fi
    sleep 1
done
wait "$CPID" 2>/dev/null; crc=$?
if [ -s "$RCF" ]; then exit "$(cat "$RCF")"; fi
exit "$crc"
