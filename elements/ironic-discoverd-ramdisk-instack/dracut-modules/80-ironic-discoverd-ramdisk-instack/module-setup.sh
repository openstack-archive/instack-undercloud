#!/bin/bash

# Dracut is bash too, and it doesn't play nicely with our usual sets
# dib-lint: disable=setu sete setpipefail

check() {
    return 0
}

depends() {
    return 0
}

install() {
    set -x
    # Something in this directory gets missed by the python-deps call below.
    for i in $(find /usr/lib64/python2.7/ -type f); do
        inst $i
    done
    for i in $(find /usr/lib/python2.7/ -type f); do
        inst $i
    done
    # $moddir/python-deps /bin/hardware-detect | while read dep; do
        # case "$dep" in
            # *.so) inst_library $dep ;;
            # *.py) inst_simple $dep ;;
            # *) inst $dep ;;
        # esac
    # done
}
