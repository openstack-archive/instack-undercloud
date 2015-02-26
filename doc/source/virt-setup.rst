Virtual Environment Setup
=========================

instack-undercloud can be deployed in a virtual environment using virtual
machines instead of actual baremetal. One baremetal machine is still needed to
act as the host for the virtual machines.

instack-undercloud contains the necessary tooling to create and configure the
environment.

Minimum System Requirements
---------------------------

This setup creates 5 virtual machines consisting of 4GB of memory and 40GB of
disk space on each. The virtual machine disk files are thinly provisioned and
will not take up the full 40GB initially.

The minimum system requirements for the virtual host machine are:

* A baremetal machine with virtualization hardware extenstions enabled.
  Nested KVM is **not** supported.
* At least (1) quad core CPU
* 12GB free memory
* 120GB disk space [#]_

If you want to increase the scaling of one or more overcloud nodes, you will
need to ensure you have enough memory and disk space.

Preparing the Host Machine
--------------------------

#. Install RHEL 7.1 Server x86_64.
#. Make sure sshd service is installed and running.
#. The user performing all of the installation steps on the virt host needs to
   have sudo enabled. You can use an existing user or use the following commands
   to create a new user called stack with password-less sudo enabled. Do not run
   the rest of the steps in this guide as root.

    * Example commands to create a user::

        sudo useradd stack
        sudo passwd stack  # specify a password
        echo "stack ALL=(root) NOPASSWD:ALL" | sudo tee -a /etc/sudoers.d/stack
        sudo chmod 0440 /etc/sudoers.d/stack

#. Make sure you are logged in as the non-root user you intend to use.
#. Add export of LIBVIRT_DEFAULT_URI to your bashrc file::

    echo 'export LIBVIRT_DEFAULT_URI="qemu:///system"' >> ~/.bashrc

#. Download and execute the instack-undercloud setup script::

    curl https://raw.githubusercontent.com/rdo-management/instack-undercloud/master/scripts/instack-setup-host-rhel7 | bash -x

#. Install instack-undercloud::

    sudo yum install instack-undercloud

#. Run scripts to install required dependencies::

    source /usr/libexec/openstack-tripleo/devtest_variables.sh
    tripleo install-dependencies
    tripleo set-usergroup-membership
    # The previous command has added the user to the libvirtd group, so we need to login to the new group
    newgrp libvirtd
    newgrp

#. Download the RHEL 7.1 cloud image or copy it over from a different
   location::

    curl -O http://download.devel.redhat.com/brewroot/packages/rhel-guest-image/7.1/20150203.1/images/rhel-guest-image-7.1-20150203.1.x86_64.qcow2

#. Source rhel7rc to set appropriate environment variables::

    source /usr/share/instack-undercloud/rhel7rc
    export DIB_YUM_REPO_CONF=/etc/yum.repos.d/rhos-release-6-rhel-7.1.repo

#. Run the script to setup your virtual environment::

    instack-virt-setup

When the script has completed successfully it will output the IP address of the
instack vm that has now been installed with a base OS.

Running virsh list --all will show you now have one virtual machine called
*instack* and 4 called *baremetal[0-3]*.

You can ssh to the instack vm as the root user::

        ssh root@<instack-vm-ip>

The vm contains a ``stack`` user to be used for installing the undercloud. You
can ``su - stack`` to switch to the stack user account.

.. rubric:: Footnotes

.. [#]  Note that some default partitioning scheme will most likely not provide
    enough space to the partition containing the default path for libvirt image
    storage (/var/lib/libvirt/images). The easiest fix is to customize the
    partition layout at the time of install to provide at least 200 GB of space for
    that path.
