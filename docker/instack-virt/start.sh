#!/bin/bash

for i in $(seq 0 4); do 
    if [ ! -f /var/lib/libvirt/images/baremetal_$i.qcow2 ]; then
	qemu-img create -f qcow2 /var/lib/libvirt/images/baremetal_$i.qcow2 31G
    fi
done

if [ ! -f /var/lib/libvirt/images/instack.qcow2 ]; then
    qemu-img create -f qcow2 -b /var/lib/libvirt/base-images/instack.qcow2 /var/lib/libvirt/images/instack.qcow2
fi

/usr/share/openvswitch/scripts/ovs-ctl start --system-id=random
ovs-vsctl list-br | grep brbm || ovs-vsctl add-br brbm

supervisord -n
