#!/bin/bash

export DIB_INSTALLTYPE_os_disk_config="${DIB_INSTALLTYPE_os_cloud_config:-"source"}"

if [ -z "${OS_DISK_CONFIG_VENV_DIR:-}" ]; then
    export OS_DISK_CONFIG_VENV_DIR="${OPENSTACK_VENV_DIR:-"/opt/stack/venvs/os-disk-config"}"
fi
