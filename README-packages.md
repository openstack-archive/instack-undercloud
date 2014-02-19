Undercloud Install via instack
==============================

1. Enable the openstack-m repository

        sudo yum -y install http://repos.fedorapeople.org/repos/openstack-m/openstack-m/openstack-m-release-icehouse-1.noarch.rpm

2. Install instack-undercloud

        sudo yum -y install instack-undercloud

2. Create and edit your answers file. The descriptions of the parameters that
   can be set are in the sample answers file.

        # Answers file must exist in home directory for now
        cp /usr/share/doc/instack-undercloud/instack-virt.answers.sample ~/instack.answers
        # Perform any answer file edits

3. Run script to install undercloud. The script will produce a lot of output on
   the sceen. It also logs to ~/.instack/install-undercloud.log. You should see
   `install-undercloud Complete!` at the end of a successful run.

        install-undercloud-packages


That completes the Undercloud install. To proceed with deploying and using the
Overcloud see [Overcloud](Overcloud.md).
