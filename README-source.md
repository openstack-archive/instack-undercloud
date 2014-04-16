instack-undercloud via source
=============================

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

4. Once the install script has run to completion, you should take note to secure and save the files
   `/root/stackrc` and `/root/tripleo-undercloud-passwords`. Both these files will be needed to interact
   with the installed undercloud. You may copy these files to your home directory to make them 
   easier to source later on, but you should try to keep them as secure and backed up as possible.

That completes the Undercloud install. To proceed with deploying and using the
Overcloud see [Overcloud-packages](Overcloud-packages.md).
