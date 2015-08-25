.. _delete_nodes:

Deleting Overcloud Nodes
========================

You can delete specific nodes from an overcloud with command::

    openstack overcloud node delete --stack $STACK_NAME --plan $PLAN_UUID <list of nova instance IDs>

This command updates number of nodes in tuskar plan and then updates heat stack
with updated numbers and list of resource IDs (which represent nodes) to be
deleted.

.. note::
   If you passed any extra environment files when you created the overcloud (for
   instance, in order to configure :doc:`network isolation
   <../advanced_deployment/network_isolation>`), you must pass them again here
   using the ``-e`` or ``--environment-file`` option to avoid making undesired
   changes to the overcloud.


.. note::
   Before deleting a compute node please make sure that the node is quiesced,
   see :ref:`quiesce_compute`.

.. note::
   A list of nova instance IDs can be listed with command::

       nova list

Deleting nodes without using Tuskar
-----------------------------------

If the overcloud was :doc:`deployed from heat templates directly
<../advanced_deployment/template_deploy>` then use the ``--templates``
parameter when deleting nodes::

   openstack overcloud node delete --stack $STACK_NAME --templates [templates dir] <list of nova instance IDs>

If you passed any extra environment files when you created the overcloud (for
instance, in order to configure :doc:`network isolation
<../advanced_deployment/network_isolation>`), you must pass them again here
using the ``-e`` or ``--environment-file`` option to avoid making undesired
changes to the overcloud.
