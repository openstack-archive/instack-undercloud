instack-undercloud via packages
===============================

These steps can be used to install the undercloud from tripleo packages on the
already setup instack vm. The packages are pulled from the copr repo for now.

1. Once you are ssh'd into the instack vm as the stack user, setup the copr repo

        sudo curl -o /etc/yum.repos.d/slagle-openstack-m.repo https://copr.fedoraproject.org/coprs/slagle/openstack-m/repo/fedora-20/slagle-openstack-m-fedora-20.repo

2. Install instack-undercloud

        sudo yum -y install instack-undercloud

3. Run the installation script

        instack-install-undercloud-source
