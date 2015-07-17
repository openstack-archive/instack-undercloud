Configuring Cinder with a NetApp Backend
========================================

This guide assumes that your undercloud is already installed and ready to
deploy an overcloud.

Deploying the Overcloud
-----------------------
.. note::

    The :doc:`template_deploy` doc has a more detailed explanation of the
    following steps.

#. Copy the NetApp configuration file to your home directory::

     sudo cp /usr/share/openstack-tripleo-heat-templates/environments/cinder-netapp-config.yaml ~

#. Edit the permissions (user is typically ``stack``)::

    sudo chown $USER ~/cinder-netapp-config.yaml
    sudo chmod 755 ~/cinder-netapp-config.yaml


#. Edit the parameters in this file to fit your requirements. Ensure that the following line is changed::

       OS::TripleO::ControllerExtraConfigPre: /usr/share/openstack-tripleo-heat-templates/puppet/extraconfig/pre_deploy/controller/cinder-netapp.yaml


#. Continue following the TripleO instructions for deploying an overcloud.
   Before entering the command to deploy the overcloud, add the environment
   file that you just configured as an argument::

    openstack overcloud deploy --templates -e ~/cinder-netapp-config.yaml

#. Wait for the completion of the overcloud deployment process.


Creating a NetApp Volume
------------------------

.. note::

    The following steps will refer to running commands as an admin user or a
    tenant user. Sourcing the ``overcloudrc`` file will authenticate you as
    the admin user. You can then create a tenant user and use environment
    files to switch between them.

#. Create a new volume type that maps to the new NetApp backend [admin]::

    cinder type-create [name]
    cinder type-key [name] set volume_backend_name=tripleo_netapp

#. Create the volume [admin]::

    cinder create --volume-type [type name] [size of volume]

#. Attach the volume to a server::

     nova volume-attach <server> <volume> <device>

