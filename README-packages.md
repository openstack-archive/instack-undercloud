instack-undercloud via packages
===============================

The commands in these instructions should be applied to the baremetal machine or the instack virtual machine to create
an undercloud.  It helps when setting up the undercloud to use a user with passwordless sudo enabled.  If you're using a
virtual machine environment, the stack user in the default instack vm is already configured with passwordless sudo.

1. Enable the RDO icehouse repository

        sudo yum install -y http://rdo.fedorapeople.org/openstack-icehouse/rdo-release-icehouse.rpm

1. Optional. You can enable the RDO staging repository to get newer packages if available.

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

2. Create and edit your answers file. The descriptions of the parameters that can be set are in the sample answers file.

        # Answers file must exist in home directory for now
        # Use either the baremetal or virt sample answers file
        # cp /usr/share/doc/instack-undercloud/instack-baremetal.answers.sample ~/instack.answers
        # cp /usr/share/doc/instack-undercloud/instack-virt.answers.sample ~/instack.answers
        # Perform any answer file edits

3. Run script to install undercloud. The script will produce a lot of output on
   the sceen. It also logs to ~/.instack/install-undercloud.log. You should see
   `install-undercloud Complete!` at the end of a successful run.

        instack-install-undercloud-packages
        
4. Once the install script has run to completion, you should take note to secure and save the files
   `/root/stackrc` and `/root/tripleo-undercloud-passwords`. Both these files will be needed to interact
   with the installed undercloud. You may copy these files to your home directory to make them 
   easier to source later on, but you should try to keep them as secure and backed up as possible.

That completes the Undercloud install. To proceed with deploying and using the
Overcloud see [Overcloud-packages](Overcloud-packages.md).

To access horizon on the undercloud, create an ssh tunnel on the virt host where 192.168.122.55 should be changed to
reflect your instack virtual machine's actual IP address.  This will allow you to use horizon on instack from your virt
host.  If you need to connect remotely through the virt host, you can chain ssh tunnels as needed.  Note: Depending on
your virt host configuration, you may need to open up the correct port(s) in iptables.

       ssh -g -N -L 8080:192.168.122.55:80 `hostname`

The default user and password are found in the stackrc file on the instack virtual machine, OS_USERNAME and OS_PASSWORD.
You can read more about using the dashboard in the [User Guide](http://docs.openstack.org/user-guide/content/log_in_dashboard.html).
