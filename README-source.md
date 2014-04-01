instack-undercloud via source
=============================

1. Enable the openstack-m repository

        sudo yum -y install http://repos.fedorapeople.org/repos/openstack-m/openstack-m/openstack-m-release-icehouse-2.noarch.rpm

1. Enable the fedora-openstack-m-testing yum repository.

        sudo yum -y install yum-utils
        sudo yum-config-manager --enable fedora-openstack-m-testing

1. Clone this repository and instack

        git clone https://github.com/agroup/instack-undercloud
        git clone https://github.com/agroup/instack

2. Create and edit your answers file. The descriptions of the parameters that
   can be set are in the sample answers file.

        # Answers file must exist in home directory for now
        # Use either the baremetal or virt sample answers file
        # cp instack-undercloud/instack-baremetal.answers.sample ~/instack.answers
        # cp instack-undercloud/instack-virt.answers.sample ~/instack.answers
        # Perform any answer file edits

4. Add the instack-undercloud scripts directory to your $PATH for convenience

        export PATH=instack-undercloud/scripts:$PATH

3. Run script to install undercloud. The script will produce a lot of output on
   the sceen. It also logs to ~/.instack/install-undercloud.log. You should see
   `install-undercloud Complete!` at the end of a successful run.

        instack-install-undercloud


That completes the Undercloud install. To proceed with deploying and using the
Overcloud see [Overcloud-packages](Overcloud-packages.md).
