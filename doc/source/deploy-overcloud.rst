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

