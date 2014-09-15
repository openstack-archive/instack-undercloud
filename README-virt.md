instack-undercloud virt setup
=============================

You should select a host machine with at least 12G of memory and 200G disk space. The virt setup creates 5 virtual
machines consisting of 2G of memory and 30G of disk space each.  If you do not plan to deploy Block Storage or Swift
Storage nodes, you can delete those virtual machines and require less space accordingly.  Most of the virtual machine
disk files are thinly provisioned and won't take up the full 30G.  The undercloud is not thinly provisioned and is
completely pre-allocated.

If you're connecting to the virt host remotely from ssh, you will need to use the -t flag to force pseudo-tty
allocation or enable notty via a $USER.notty file.

Do not use the root user for executing any instack-undercloud scripts.  Some programs of libguestfs-tools are not
designed to work with the root user.  All of the instack-undercloud scripts were developed and tested by using a normal
user with sudo privileges.

Some recommended default environment variables before starting:

        # disk size in GB to set for each virtual machine created
        export NODE_DISK=30

        # memory in MB allocated for each virtual machine created
        export NODE_MEM=3072

        # Operating system distribution to set for each virtual machine created
        export NODE_DIST=fedora

        # CPU count assigned to each virtual machine created
        export NODE_CPU=1

        # 64 bit architecture
        export NODE_ARCH=amd64

1. Add export of LIVBIRT_DEFAULT_URI to your bashrc file.

        echo 'export LIBVIRT_DEFAULT_URI="qemu:///system"' >> ~/.bashrc

1. Install the openstack-m repository

        sudo yum -y install http://repos.fedorapeople.org/repos/openstack-m/openstack-m/openstack-m-release-icehouse-2.noarch.rpm

1. Enable the fedora-openstack-m-testing yum repository.

        sudo yum -y install yum-utils
        sudo yum-config-manager --enable fedora-openstack-m-testing

1. Install instack-undercloud

        sudo yum -y install instack-undercloud

1. Install required dependencies for virt

        sudo yum install -y libguestfs-tools
        source /usr/libexec/openstack-tripleo/devtest_variables.sh
        tripleo install-dependencies

   After running this command, you will need to log out and log back in for the changes to be applied.  If you plan to
   use virt-manager or boxes to visually manage the virtual machines created in the next step, this would be a good time
   to install those tools now.

1. Run script to setup your virtual environment.  If you'd like to customize the root password, export an environment
   variable UNDERCLOUD_ROOT_PASSWORD.  If you prefer to customize the name of the Undercloud virtual machine to
   something besides instack, export the environment variable UNDERCLOUD_VM_NAME.

        export NODE_DISK=30
        instack-virt-setup

   You should now have a vm called instack that you can use for the instack-undercloud installation that contains a minimal
   install of Fedora 20 x86_64. The instack vm contains a user "stack" that uses the password "stack" and is granted
   password-less sudo privileges.  The root password is displayed in the standard output unless you set it using
   UNDERCLOUD_ROOT_PASSWORD.

1. Get IP Address

   You'll need to start the instack virtual machine and obtain its IP address.  You can use your preferred virtual
   machine management software or follow the steps below.

        virsh start instack
        cat /var/lib/libvirt/dnsmasq/default.leases | grep $(tripleo get-vm-mac instack) | awk '{print $3;}'

1. Get MAC addresses

   When setting up the undercloud on the instack virtual machine, you will need the MAC addresses of the baremetal node
   virtual machines.  Use the following command to obtain the list of addresses you can add to your deploy-overcloudrc
   file later.

         for i in $(seq 0 3); do echo -n $(tripleo get-vm-mac baremetal_$i) " "; done; echo

5. Log into your instack virtual machine.  Create the virtual-power-key and copy it to the virt host.  The user in
   ssh-copy-id should match the VIRTUAL_POWER_USER and the ip should match the VIRTUAL_POWER_HOST in your
   instack.answers file.

        ssh-keygen -t rsa -N '' -C virtual-power-key -f virtual-power-key
        ssh-copy-id -i virtual-power-key.pub stack@192.168.122.1

Return to [README-packages](README-packages.md) to continue with installing the
undercloud on the instack vm.
