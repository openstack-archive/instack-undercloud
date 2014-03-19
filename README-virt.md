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

        instack-virt-setup


You should now have a vm called instack that you can use for the
instack-undercloud installation. Start and logon to the vm, then return to the (README)[README.md] and choose
either a source or package based install.
