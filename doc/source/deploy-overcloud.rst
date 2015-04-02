Deploying the Overcloud
=======================

All the commands on this page require that the appropriate stackrc file has
been sourced into the environment::

    source stackrc

Registering Nodes
-----------------

Register nodes for your deployment with Ironic::

    instack-ironic-deployment --nodes-json instackenv.json --register-nodes

Discovering Nodes
-----------------

Discover hardware attributes of nodes and match them to a deployment profile:

.. admonition:: Ceph
   :class: ceph-tag

   When deploying Ceph, you will need to configure the ``edeploy`` plugin so
   that it will assign the ``ceph-storage`` profile to at least one system. To
   do so, you need to **prepend** the following ``('ceph-storage', '1')`` into
   the list of profiles defined in ``/etc/edeploy/state``, before initiating the
   nodes discovery. [#]_

::

    instack-ironic-deployment --discover-nodes

Check what profiles were matched for the discovered nodes::

    instack-ironic-deployment --show-profile

Deploying Nodes
---------------

Create the necessary flavors::

    instack-ironic-deployment --setup-flavors

.. admonition:: Baremetal
   :class: baremetal-tag

   Copy the sample overcloudrc file and edit to reflect your environment. Then source this file::

      cp /usr/share/instack-undercloud/deploy-baremetal-overcloudrc ~/deploy-overcloudrc
      source deploy-overcloudrc

Deploy the overcloud (default of 1 compute and 1 control):

.. admonition:: Ceph
   :class: ceph-tag

   When deploying Ceph, specify the number of Ceph OSD nodes to be deployed
   with::

       export CEPHSTORAGESCALE=1

::

    instack-deploy-overcloud

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

    instack-deploy-overcloud

.. rubric:: Footnotes

.. [#]  In the ``('ceph-storage', '1')`` setting, 1 represents the number of
        systems to be tagged with such a profile as opposed to a boolean
        value.
