.. _replace_controller:

Replacing a Controller Node
===========================

Replace Failed Node
-------------------

First, create a YAML file defining node index to remove. Node index reflects
suffix of instance name in `nova list` output. In this following text
`overcloud-controller-1` node is replaced with `overcloud-controller-3`::

    $ cat ~/remove.yaml
    parameters:
      ControllerRemovalPolicies:
          [{'resource_list': ['1']}]

Then, re-deploy overcloud including the extra environment file::

    openstack overcloud deploy --templates --control-scale 3 -e ~/remove.yaml

The old node will be removed and a new one will be added.
Because some puppet modules don't support nodes replacement, re-deployment
fails and a couple of manual changes are needed to fix controller nodes setup.
Connect to one of remaining controller nodes and delete the failed node
from Pacemaker/Corosync cluster::

    crm_node -R overcloud-controller-1 --force

Delete the failed node from RabbitMQ cluster::

    rabbitmqctl forget_cluster_node rabbit@overcloud-controller-1

Delete the failed node from MongoDB::

    # connect to MongoDB on any of remaining nodes:
    mongo --host <node ip>
    # check status of MongoDB cluster:
    rs.status()
    # remove the failed node:
    rs.remove('<node_ip>:27017')

Update list of nodes in Galera cluster::

    pcs resource update galera wsrep_cluster_address=gcomm://overcloud-controller-0,overcloud-controller-3,overcloud-controller-2

Start Pacemaker/Corosync on the new node::

    pcs cluster node add overcloud-controller-3
    pcs cluster start overcloud-controller-3

Enable keystone service on the new node::

    copy /etc/keystone from a remaining node to the new node
    set admin_bind_host and public_bind_host in /etc/keystone/keystone.conf to node's IP
    pcs resource cleanup openstack-keystone-clone overcloud-controller-3

Re-deploy overcloud again::

    openstack overcloud deploy --templates --control-scale 3

.. note::

    If deployment fails with error `Failed to call refresh: Could not restart Service[httpd]`
    then try re-deploy again.


Completing Update
-----------------

Delete the failed node from `/etc/corosync/corosync.conf` file and restart
Corosync one by one on each node::

    systemctl restart corosync

When re-deployment finishes, connect to one of controller nodes and start
services on the new node::

    pcs resource cleanup neutron-server-clone
    pcs resource cleanup openstack-nova-api-clone
    pcs resource cleanup openstack-nova-consoleauth-clone
    pcs resource cleanup openstack-heat-engine-clone
    pcs resource cleanup openstack-cinder-api-clone
    pcs resource cleanup openstack-glance-registry-clone
    pcs resource cleanup httpd-clone


Replacing Bootstrap Node
------------------------

If node with index 0 is being replaced it's necessary to edit heat templates
and change bootstrap node index before starting replacement. Open
`overcloud-without-mergepy.yaml` file in root directory of heat templates and
change lines::

    bootstrap_nodeid: {get_attr: [Controller, resource.0.hostname]}
    bootstrap_nodeid_ip: {get_attr: [Controller, resource.0.ip_address]}

to::

    bootstrap_nodeid: {get_attr: [Controller, resource.1.hostname]}
    bootstrap_nodeid_ip: {get_attr: [Controller, resource.1.ip_address]}

Tuskar doesn't support template editing so it's possible to do this change only
if overcloud is deployed with :doc:`templates directly <../advanced_deployment/template_deploy>`.
