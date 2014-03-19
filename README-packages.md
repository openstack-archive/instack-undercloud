instack-undercloud via packages
===============================
    
1. Enable the openstack-m repository

        sudo yum -y install http://repos.fedorapeople.org/repos/openstack-m/openstack-m/openstack-m-release-icehouse-2.noarch.rpm

1. Enable the fedora-openstack-m-testing yum repository.

        sudo yum -y install yum-utils
        sudo yum-config-manager --enable fedora-openstack-m-testing

2. Install instack-undercloud

        sudo yum -y install instack-undercloud

2. Create and edit your answers file. The descriptions of the parameters that
   can be set are in the sample answers file.

        # Answers file must exist in home directory for now
        # Use either the baremetal or virt sample answers file
        # cp /usr/share/doc/instack-undercloud/instack-baremetal.answers.sample ~/instack.answers
        # cp /usr/share/doc/instack-undercloud/instack-virt.answers.sample ~/instack.answers
        # Perform any answer file edits

3. Run script to install undercloud. The script will produce a lot of output on
   the sceen. It also logs to ~/.instack/install-undercloud.log. You should see
   `install-undercloud Complete!` at the end of a successful run.

        instack-install-undercloud-packages
        
4. Configure tuskar. Edit /etc/tuskar/tuskar.conf so the following settings are enabled: 
   
        connection=sqlite:////home/stack/tuskar.sqlite   
        tht_local_dir=/usr/share/tripleo-heat-templates/
        username=admin  # OS_USERNAME from /etc/sysconfig/stackrc
        password=unset   # OS_PASSWORD from /etc/sysconfig/stackrc
        tenant_name=admin  # OS_TENANT_NAME from /etc/sysconfig/stackrc
        auth_url=http://localhost:5000/v2.0   
        insecure=true

5. Initialise the tuskar database and restart the service

        sudo tuskar-dbsync --config-file /etc/tuskar/tuskar.conf
        sudo service openstack-tuskar-api restart


That completes the Undercloud install. To proceed with deploying and using the
Overcloud see [Overcloud-packages](Overcloud-packages.md).
