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
    for i in $(find /usr/lib64/python2.7/ -type f); do
        inst $i
    done
    for i in $(find /usr/lib/python2.7/ -type f); do
        inst $i
    done
    inst /etc/ssh/sshd_config
}

installkernel() {
    instmods sg
    instmods ipmi_msghandler
    instmods ipmi_si
    instmods ipmi_devintf
}
