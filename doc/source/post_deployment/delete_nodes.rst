.. _delete_nodes:

Deleting Overcloud Nodes
========================

You can delete specific nodes from an overcloud with command::

    openstack overcloud node delete --stack $STACK --plan $PLAN_UUID <list of nova instance IDs>

This command updates number of nodes in tuskar plan and then updates heat stack
with updated numbers and list of resource IDs (which represent nodes) to be
deleted.

.. note::
   Before deleting a compute node please make sure that the node is quiesced,
   see :ref:`quiesce_compute`.

.. note::
   A list of nova instance IDs can be listed with command::

       nova list

Deleting nodes without using Tuskar
-----------------------------------
If the overcloud was deployed from heat templates directly then use
`--templates` parameter when deleting nodes::

   openstack overcloud node delete --stack $STACK --templates [templates dir] <list of nova instance IDs>
