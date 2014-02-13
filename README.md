Undercloud Install via instack
==============================

1. Clone this repository and instack

        git clone https://github.com/slagle/instack-undercloud
        git clone https://github.com/slagle/instack

2. Create and edit your answers file. The descriptions of the parameters that
   can be set are in the sample answers file.

        cd instack-undercloud
        cp instack.answers.sample instack.answers
        # Return back to directory where instack was cloned
        cd ..

3. Run script to install undercloud. The script will produce a lot of output on
   the sceen. It also logs to ~/.instack/install-undercloud.log. You should see
   `install-undercloud Complete!` at the end of a successful run.

        instack-undercloud/scripts/install-undercloud

4. The install script has to manipulate your $PATH (until we get everything
   packaged), so you'll need to start a new shell.

        bash

4. Copy the stackrc file to your homedir so that you can use it a normal user.

        sudo cp /root/stackrc .
        sudo chown $USER: stackrc
        source stackrc

4. Add your ssh key pair to nova

        user-config

5. Download the deployment kernel and ramdisk

        curl -L -O http://fedorapeople.org/~slagle/slagle-tripleo-images-fedora-i2/deploy-ramdisk.initramfs
        curl -L -O http://fedorapeople.org/~slagle/slagle-tripleo-images-fedora-i2/deploy-ramdisk.kernel

5. Download overcloud images

        curl -L -O http://file.rdu.redhat.com/~jslagle/tripleo-images-fedora-i2-dib-patches/overcloud-compute.qcow2
        curl -L -O http://file.rdu.redhat.com/~jslagle/tripleo-images-fedora-i2-dib-patches/overcloud-control.qcow2

5. Load images into glance

        load-image overcloud-control.qcow2
        load-image overcloud-compute.qcow2

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
        setup-baremetal $CPU $MEM $DISK $ARCH "$MACS" undercloud "$PM_IPS" "$PM_USERS" "$PM_PASSWORDS"

7. Create your overcloud heat template. You can adjust COMPUTESCALE to launch
   more than one compute node if you choose to.

        sudo make -C /opt/stack/tripleo-heat-templates overcloud.yaml COMPUTESCALE=1

8. Create and source the overcloud passwords

        setup-overcloud-passwords
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
