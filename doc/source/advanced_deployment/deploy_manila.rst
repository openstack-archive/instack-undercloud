Deploying Manila in the Overcloud
=================================

This guide assumes that your undercloud is already installed and ready to
deploy an overcloud with Manila enabled.

Deploying the Overcloud
-----------------------
.. note::

    The :doc:`template_deploy` doc has a more detailed explanation of the
    following steps.

#. Copy the Manila driver-specific configuration file to your home directory:

     - Generic driver::

          sudo cp /usr/share/openstack-tripleo-heat-templates/environments/manila-generic-config.yaml ~

     - NetApp driver::

         sudo cp /usr/share/openstack-tripleo-heat-templates/environments/manila-netapp-config.yaml ~

#. Edit the permissions (user is typically ``stack``)::

    sudo chown $USER ~/manila-*-config.yaml
    sudo chmod 755 ~/manila-*-config.yaml


#. Edit the parameters in this file to fit your requirements.
    - If you're using the generic driver, ensure that the service image
      details correspond to the service image you intend to load.
    - Ensure that the following line is changed::

       OS::TripleO::ControllerExtraConfigPre: /usr/share/openstack-tripleo-heat-templates/puppet/extraconfig/pre_deploy/controller/manila-[generic or netapp].yaml


#. Continue following the TripleO instructions for deploying an overcloud.
   Before entering the command to deploy the overcloud, add the environment
   file that you just configured as an argument::

    openstack overcloud deploy --templates -e ~/manila-[generic or netapp]-config.yaml

#. Wait for the completion of the overcloud deployment process.


Creating the Share
------------------

.. note::

    The following steps will refer to running commands as an admin user or a
    tenant user. Sourcing the ``overcloudrc`` file will authenticate you as
    the admin user. You can then create a tenant user and use environment
    files to switch between them.

#. Upload a service image:

   .. note::

       This step is only required for the generic driver.

   Download a Manila service image to be used for share servers and upload it
   to Glance so that Manila can use it [tenant]::

       glance image-create --name manila-service-image --disk-format qcow2 --container-format bare --file manila_service_image.qcow2

#. Create a share network to host the shares:

   - Create the overcloud networks. The
     :doc:`../basic_deployment/basic_deployment` doc has a more detailed
     explanation about creating the network and subnet. Note that you may also
     need to perform the following steps to get Manila working::

       neutron router-create router1
       neutron router-interface-add router1 [subnet id]

   - List the networks and subnets [tenant]::

       neutron net-list && neutron subnet-list

   - Create a share network (typically using the private default-net net/subnet)
     [tenant]::

       manila share-network-create --neutron-net-id [net] --neutron-subnet-id [subnet]

#. Create a new share type (yes/no is for specifying if the driver handles
   share servers) [admin]::

    manila type-create [name] [yes/no]

#. Create the share [tenant]::

    manila create --share-network [share net ID] --share-type [type name] [nfs/cifs] [size of share]


Accessing the Share
-------------------

#. To access the share, create a new VM on the same Neutron network that was
   used to create the share network::

    nova boot --image [image ID] --flavor [flavor ID] --nic net-id=[network ID] [name]

#. Allow access to the VM you just created::

    manila access-allow [share ID] ip [IP address of VM]

#. Run ``manila list`` and ensure that the share is available.

#. Log into the VM::

    ssh [user]@[IP]

.. note::

    You may need to configure Neutron security rules to access the
    VM. That is not in the scope of this document, so it will not be covered
    here.

5. In the VM, execute::

    sudo mount [export location] [folder to mount to]

6. Ensure the share is mounted by looking at the bottom of the output of the
   ``mount`` command.

7. That's it - you're ready to start using Manila!

