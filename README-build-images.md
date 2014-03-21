Overcloud image building
========================
    
1. Enable the openstack-m repository

        sudo yum -y install http://repos.fedorapeople.org/repos/openstack-m/openstack-m/openstack-m-release-icehouse-2.noarch.rpm

1. Enable the fedora-openstack-m-testing yum repository.

        sudo yum -y install yum-utils
        sudo yum-config-manager --enable fedora-openstack-m-testing

2. Install instack-undercloud

        sudo yum -y install instack-undercloud

2. Run script to build images

        instack-build-images
