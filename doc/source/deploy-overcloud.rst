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

Discover hardware attributes of nodes and match them to a deployment profile::

    instack-ironic-deployment --discover-nodes

Check what profiles were matched for the discovered nodes::

    instack-ironic-deployment --show-profile

Deploying Nodes
---------------

Create the necessary flavors::

    instack-ironic-deployment --setup-flavors

Deploy the the *openstack-full* image (default of 1 compute and 1 control)::

    instack-deploy-overcloud


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
