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
    inst /usr/bin/python
    while IFS='' read -r -d '' i; do
        inst "$i"
    done < <(find /usr/lib64/python2.7/ /usr/lib/python2.7/ -type f -print0)
    inst /etc/ssh/sshd_config
}

installkernel() {
    instmods sg
    instmods ipmi_msghandler
    instmods ipmi_si
    instmods ipmi_devintf
}
