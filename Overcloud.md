Overcloud
=========
This page details how to deploy and use an Overcloud once the Undercloud is
installed.

Deploying
---------
Note that the steps below for deploying are also captured in a script at
scripts/deploy-overcloud.

1. In case you're still using the same shell, the install script has to manipulate your $PATH (until we get everything
   packaged), so you'll need to start a new shell environment.

        bash

4. Copy the stackrc file to your homedir so that you can use it a normal user.

        source /etc/sysconfig/stackrc

4. Add your ssh key pair to nova

        tripleo user-config

5. Download the deployment kernel and ramdisk

        curl -L -O http://file.rdu.redhat.com/~jslagle/tripleo-images-rdo-icehouse/deploy-ramdisk.initramfs
        curl -L -O http://file.rdu.redhat.com/~jslagle/tripleo-images-rdo-icehouse/deploy-ramdisk.kernel

5. Download overcloud images

        curl -L -O http://file.rdu.redhat.com/~jslagle/tripleo-images-rdo-icehouse/overcloud-control.qcow2
        curl -L -O http://file.rdu.redhat.com/~jslagle/tripleo-images-rdo-icehouse/overcloud-compute.qcow2

5. Load images into glance

        tripleo load-image overcloud-control.qcow2
        tripleo load-image overcloud-compute.qcow2

6. Use the setup-baremetal script to add your baremetal nodes

        # setup-baremetal requires this to be set
        export TRIPLEO_ROOT=.
        # $CPU = cpu count per node
        # $MEM = memory per node in MB
        # $DISK = disk per node in GB
        # $ARCH = architecture of each node, i386 or amd64
        # $MACS = space separated list of node mac addresses
        # $PM_IPS = space separated list of power management IP addresses
        # $PM_USERS = space separated list of power management users
        # $PM_PASSWORDS = space separated list of power management passwords
        # $MACS and $PM_* variables should be in the same node order, e.g., the 
        #   first MAC address should correspond to the first power management
        #   IP, etc.
        tripleo setup-baremetal $CPU $MEM $DISK $ARCH "$MACS" undercloud "$PM_IPS" "$PM_USERS" "$PM_PASSWORDS"

7. Create your overcloud heat template. You can adjust COMPUTESCALE to launch
   more than one compute node if you choose to.

        sudo make -C /opt/stack/tripleo-heat-templates overcloud.yaml COMPUTESCALE=1

8. Create and source the overcloud passwords

        tripleo setup-overcloud-passwords
        source tripleo-overcloud-passwords

9. Deploy the overcloud

        # Define the interface that will be bridged onto the Neutron defined
        # network.
        NeutronPublicInterface=eth0
        # Define the overcloud libvirt type for virtualization. kvm for
        # baremetal, qemu for an overcloud running in vm's.
        OVERCLOUD_LIBVIRT_TYPE=kvm

        heat stack-create -f /opt/stack/tripleo-heat-templates/overcloud.yaml \
            -P AdminToken=${OVERCLOUD_ADMIN_TOKEN} \
            -P AdminPassword=${OVERCLOUD_ADMIN_PASSWORD} \
            -P CinderPassword=${OVERCLOUD_CINDER_PASSWORD} \
            -P GlancePassword=${OVERCLOUD_GLANCE_PASSWORD} \
            -P HeatPassword=${OVERCLOUD_HEAT_PASSWORD} \
            -P NeutronPassword=${OVERCLOUD_NEUTRON_PASSWORD} \
            -P NovaPassword=${OVERCLOUD_NOVA_PASSWORD} \
            -P NeutronPublicInterface=$NeutronPublicInterface \
            -P SwiftPassword=${OVERCLOUD_SWIFT_PASSWORD} \
            -P SwiftHashSuffix=${OVERCLOUD_SWIFT_HASH} \
            -P NovaComputeLibvirtType=$OVERCLOUD_LIBVIRT_TYPE \
            overcloud

Using the Overcloud
-------------------
The scripted steps for configuring and using the Overcloud by launching a
single cirros instance in it are scripted at scripts/overcloud.


You can also use the devtest instructions to walk through it manually. Start off with step 11 from
http://docs.openstack.org/developer/tripleo-incubator/devtest_overcloud.html.

You won't be able to follow the steps exactly. Here's what you need to modify:

* When $TRIPLEO_ROOT is used, replace with /opt/stack instead
* When running setup-neutron, correct subnet ranges will need to be used if
  192.0.2.0/24 is not applicable to the environment.
* When loading the user.qcow2 image into glance, I would use a cirros image
  instead. Download the cirros image from
  https://launchpad.net/cirros/trunk/0.3.0/+download/cirros-0.3.0-x86_64-disk.img
  and specify the path to the downloaded file when you run the glance command.
