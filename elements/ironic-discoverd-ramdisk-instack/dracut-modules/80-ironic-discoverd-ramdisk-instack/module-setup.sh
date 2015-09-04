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
    local all_of_python=()
    while IFS='' read -r -d '' i; do
        all_of_python+=("$i")
    done < <(find /usr/lib64/python2.7/ /usr/lib/python2.7/ -type f -not -name "*.pyc" -not -name "*.pyo" -print0)
    inst_multiple "${all_of_python[@]}"
    inst /etc/ssh/sshd_config
}

installkernel() {
    instmods sg
    instmods ipmi_msghandler
    instmods ipmi_si
    instmods ipmi_devintf
}
