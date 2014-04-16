Overcloud image building
========================
    
1. Enable the RDO icehouse repository

        sudo yum install -y http://rdo.fedorapeople.org/openstack-icehouse/rdo-release-icehouse.rpm

1. You can either pull instack-undercloud related RPM's from the openstack-m testing repository or the RDO staging repository for now. Decide which one you want, and enable it via the comamnds shown below.

    For openstack-m:
    
        sudo yum -y install http://repos.fedorapeople.org/repos/openstack-m/openstack-m/openstack-m-release-icehouse-2.noarch.rpm
        sudo yum -y install yum-utils
        sudo yum-config-manager --enable fedora-openstack-m-testing

    For RDO staging:
    
        sudo /bin/bash -c "cat >>/etc/yum.repos.d/rdo-staging.repo<<EOF
        [openstack-icehouse-staging]
        name=OpenStack Icehouse Staging Repository
        baseurl=http://team.virt.bos.redhat.com/openstack/openstack-icehouse/fedora-20/
        enabled=1
        skip_if_unavailable=0
        gpgcheck=0
        EOF
        "

2. Install instack-undercloud

        sudo yum -y install instack-undercloud

2. Run script to build images

        instack-build-images
