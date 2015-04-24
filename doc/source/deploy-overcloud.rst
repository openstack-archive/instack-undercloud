Deploying the Overcloud
=======================

All the commands on this page require that the appropriate stackrc file has
been sourced into the environment::

    source stackrc

Registering Nodes
-----------------

Register nodes for your deployment with Ironic::

    instack-ironic-deployment --nodes-json instackenv.json --register-nodes

.. note::
   It's not recommended to delete nodes and/or rerun this command after
   you have proceeded to the next steps. Particularly, if you start discovery
   and then re-register nodes, you won't be able to retry discovery until
   the previous one times out (1 hour by default). If you are having issues
   with nodes after registration, please follow
   :ref:`node_registration_problems`.

Introspecting Nodes
-------------------

Introspect hardware attributes of nodes::

    instack-ironic-deployment --discover-nodes

.. note:: **Introspection has to finish without errors.**
   The process can take up to 5 minutes for VM / 15 minutes for baremetal. If
   the process takes longer, see :ref:`introspection_problems`.


Ready-state configuration
-------------------------

.. admonition:: Baremetal
   :class: baremetal

   Some hardware has additional setup available, using its vendor-specific management
   interface.  See the :doc:`/vendor-specific` for details.

Deploying Nodes
---------------

Create the necessary flavors::

    instack-ironic-deployment --setup-flavors

.. admonition:: Baremetal
   :class: baremetal

   Copy the sample overcloudrc file and edit to reflect your environment. Then source this file::

      cp /usr/share/instack-undercloud/deploy-baremetal-overcloudrc ~/deploy-overcloudrc
      source deploy-overcloudrc

Deploy the overcloud (default of 1 compute and 1 control):

.. admonition:: Ceph
   :class: ceph

   When deploying Ceph, specify the number of Ceph OSD nodes to be deployed
   with::

       export CEPHSTORAGESCALE=1

   By default when Ceph is enabled the Cinder iSCSI back-end is disabled. This
   behavior may be changed by setting the environment variable::

       export CINDER_ISCSI=1

::

    instack-deploy-overcloud --tuskar

Working with the Overcloud
--------------------------

``instack-deploy-overcloud`` generates an overcloudrc file appropriate for
interacting with the deployed overcloud in the current user's home directory.
To use it, simply source the file::

    source ~/overcloudrc

To return to working with the undercloud, source the stackrc file again::

    source ~/stackrc

Redeploying the Overcloud
-------------------------

The overcloud can be redeployed when desired.

#. First, delete any existing Overcloud::

    heat stack-delete overcloud

#. Confirm the Overcloud has deleted. It may take a few minutes to delete::

    # This command should show no stack once the Delete has completed
    heat stack-list

#. Although not required, discovery can be rerun. Reset the state file and then rediscover nodes::

    sudo cp /usr/libexec/os-apply-config/templates/etc/edeploy/state /etc/edeploy/state
    instack-ironic-deployment --discover-nodes

#. Deploy the Overcloud again::

    instack-deploy-overcloud --tuskar
