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

.. note::
   Make sure you use `-i` parameter, otherwise update runs on background and
   doesn't prompt for removing of breakpoints.

.. note::
   If the update command is aborted for some reason you can always continue
   in the process by re-running same command.

Updating Packages on Overcloud Nodes Without Using Tuskar
---------------------------------------------------------

If the overcloud was :doc:`deployed from heat templates directly
<../advanced_deployment/template_deploy>` then use the ``--templates``
parameter when updating packages::

    openstack overcloud update stack --templates [templates dir] -i overcloud

If you passed any extra environment files when you created the overcloud (for
instance, in order to configure :doc:`network isolation
<../advanced_deployment/network_isolation>`), you must pass them again here
using the ``-e`` or ``--environment-file`` option to avoid making undesired
changes to the overcloud.
