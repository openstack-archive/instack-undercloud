instack-undercloud via source
=============================

1. The user performing all of the installation steps on the virt host needs to
   have password-less sudo enabled. This step is NOT optional, you must create an
   additional user. Do not run the rest of the steps as root.

         sudo useradd stack
         sudo passwd stack  # specify a password
         echo "stack ALL=(root) NOPASSWD:ALL" | sudo tee -a /etc/sudoers.d/stack
         sudo chmod 0440 /etc/sudoers.d/stack
         sudo su - stack

1. Create initial directory for instack, and clone the needed repositories.


         mkdir instack
         cd instack
         export TRIPLEO_ROOT=/home/stack/instack
         git clone https://github.com/agroup/instack-undercloud
         git clone https://git.openstack.org/openstack/tripleo-incubator


1. Complete the initial setup.

         source instack-undercloud/instack-sourcerc
         source tripleo-incubator/scripts/devtest_variables.sh
         tripleo install-dependencies
         tripleo set-usergroup-membership


1. Verify membership in the libvirtd group

         # verify you are in the libvirtd group
         id | grep libvirtd
         # if not, start a new shell to pick it up
         sudo su - stack
         cd instack
         source instack-undercloud/instack-sourcerc


1. Create the virtual environment.

         instack-virt-setup

1. Start instack vm.

         virsh start instack

1. ssh as the stack user (password is stack) to the instack vm

1. Clone instack-undercloud, source instack-sourcerc, and run script to install the undercloud from
   source. The script will produce a lot of output on the sceen. It also logs to
   ~/.instack/install-undercloud.log. You should see `install-undercloud
   Complete!` at the end of a successful run. 
   
        # Set $LKG to use the last known good working commits
        # export LKG=1
        git clone https://github.com/agroup/instack-undercloud
        source instack-undercloud/instack-sourcerc
        instack-install-undercloud-source

1. Once the install script has run to completion, you should take note to secure and save the files
   `/root/stackrc` and `/root/tripleo-undercloud-passwords`. Both these files will be needed to interact
   with the installed undercloud. You may copy these files to your home directory to make them 
   easier to source later on, but you should try to keep them as secure and backed up as possible.

That completes the Undercloud install. To proceed with deploying and using the
Overcloud see [Overcloud-packages](Overcloud-packages.md).
