instack-undercloud virt setup
=============================

1. Install the openstack-m repository

        sudo yum -y install http://repos.fedorapeople.org/repos/openstack-m/openstack-m/openstack-m-release-icehouse-2.noarch.rpm

1. Enable the fedora-openstack-m-testing yum repository.

        sudo yum -y install yum-utils
        sudo yum-config-manager --enable fedora-openstack-m-testing

1. Install instack-undercloud

        sudo yum -y install instack-undercloud

1. Run script to setup your virtual environment

        # you may need to ensure openvswtich service is installed and running for the
        # next script to run properly

        instack-virt-setup


You should now have a vm called instack that you can use for the
instack-undercloud installation. It still needs to be installed to Fedora 20
x86_64 however. You can use any method to do so, such as a live cd, kickstart,
etc.

Note that you don't have to use the pre-created instack vm and could instead create a
new one via some other method (virt-install, virt-clone, etc). If you do so
however make sure all the NIC interfaces are set to use virtio, and also
manually add an additional interface to the vm by adding the following the
libvirt xml for the domain (you may need to adjust slot as needed):

        <interface type='network'>
          <source network='brbm'/>
          <model type='virtio'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x04' function='0x0'/>
        </interface>


Once the vm is installed, start and logon to the vm, then return to the
[README](README.md) and choose either a source or package based install.

You can use the instack-virt.answers.sample file to help create an answers
file. Note that will you need to generate an ssh key for the virtual power
driver to use. See the SSH_KEY setting in the sample answers file for more
details.
