Overcloud
=========
This page details how to deploy and use an Overcloud once the Undercloud is
installed.

There are 3 scripts for convenience.

Note that deploy-overcloud can be configured for individual environments via
environment variables. The variables you can set are documented below before
the calls to the script. For their default values, see the deploy-overcloud
script itself.

1. Run the prepare-for-overcloud script to get setup. This script will
re-downloading images if they already exist in the current working directory.
If you want to force a redownload of the images, delete them first.

        instack-prepare-for-overcloud

1. If you're testing an all VM setup, copy the ssh key for the virtual power
driver user to your authorized keys file. Define $UNDERCLOUD_IP for your
environment. Skip this step if you are using all baremetal. 

        ssh $UNDERCLOUD_IP cat /opt/stack/boot-stack/virtual-power-key.pub >> ~/.ssh/authorized_keys 
        
1. Run the deploy-overcloud script to actually deploy the overcloud. Note that
   the variables must be exported so that their values are picked up by
   deploy-overcloud. If you put them in an rc file that you intend to source,
   make sure there are exports in that file as well.

        # CPU: number of cpus on baremetal nodes
        # MEM: amount of ram on baremetal nodes, in MB
        # DISK: amount of disk on baremetal nodes, in GB
        # ARCH: architecture of baremetal nodes, amd64 or i386
        # MACS: list of MAC addresses of baremetal nodes
        # PM_IPS: list of Power Management IP addresses
        # PM_USERS: list of Power Management Users
        # PM_PASSWORDS: list of Power Management Passwords
        # NeutronPublicInterface: Overcloud management interface name
        # OVERCLOUD_LIBVIRT_TYPE: Overcloud libvirt type, qemu or kvm
        # NETWORK_CIDR: neutron network cidr
        # FLOATING_IP_START: floating ip allocation start
        # FLOATING_IP_END: floating ip allocation end
        # FLOATING_IP_CIDR: floating ip network cidr
        instack-deploy-overcloud-tuskarcli

1. Run the test-overcloud script to launch a cirros image on the overcloud and
wait until it pings successfully

        instack-test-overcloud
