Scaling overcloud roles
=======================
If you want to increase or decrease resource capacity of a running overcloud,
you can start more servers of a selected role or delete some servers if
capacity should be decreased. First update the Overcloud plan with a new
number of nodes of the role::

    openstack management plan set $PLAN_UUID -S Compute-1=5

.. note::
   The role is specified including the role version. Both role names
   and role versions can be listed with command::

       openstack role list


And then re-deploy the Overcloud with the updated plan::

    openstack overcloud deploy --plan $PLAN_UUID

.. note::
   Scaling out assumes that newly added nodes has already been
   registered in Ironic.

.. note::
   When scaling down random servers of specified role will be deleted, how to
   delete specific nodes is decribed in :ref:`delete_nodes`.

Scaling overcloud roles without using Tuskar
--------------------------------------------

If the overcloud was :doc:`deployed from heat templates directly
<../advanced_deployment/template_deploy>` then you can just re-deploy the
overcloud with ``--templates`` and ``--<role>-scale`` parameters::

   openstack overcloud deploy --templates [templates dir] --compute-scale 5

If you passed any extra environment files when you created the overcloud (for
instance, in order to configure :doc:`network isolation
<../advanced_deployment/network_isolation>`), you must pass them again here
using the ``-e`` or ``--environment-file`` option to avoid making undesired
changes to the overcloud.
