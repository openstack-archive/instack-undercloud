Updating Packages on Overcloud Nodes
====================================

You can update packages on all overcloud nodes  with command::

    openstack overcloud update stack --plan $PLAN_UUID -i overcloud

This command updates UpdateIdentifier parameter in the overcloud tuskar plan
and triggers stack update operation. If this parameter is set 'yum update'
command is executed and each node. Because running update on all nodes in
parallel might be unsafe (an update of a package might involve restarting
a service), the command above sets breakpoints on each overcloud node so nodes
are updated one by one. When the update is finished on a node the command
will prompt for removing breakpoint on next one.

.. note::
   Multiple breakpoints can be removed by specifying list of nodes with a
   regular expression.

Updating Packages on Overcloud Nodes Without Using Tuskar
---------------------------------------------------------
If the overcloud was deployed from heat templates directly then use
`--templates` parameter when updating packages::

    openstack overcloud update stack --templates [templates dir] -i overcloud
