Migrating Workloads from an existing OpenStack cloud
====================================================

RDO Manager provides the ability to manage changes over time to a cloud that it
has deployed. However, it cannot automatically take over the management of
existing OpenStack clouds deployed with another installer. Since there can be
no one-size-fits-all procedure for upgrading an existing cloud to use RDO
Manager, it is recommended that a new cloud be deployed with RDO Manager and
any workloads running on an existing cloud be migrated off.

Migrating User Workloads
------------------------

Since the best way of avoiding or handling any downtime associated with moving
an application from one cloud to another is application-dependent, it is
preferable to have end users migrate their own applications at a time and in
the manner of their choosing. This can also help to spread out the network
bandwidth requirements, rather than copying a large number of snapshots in
bulk.

Ideally applications can be re-created from first principles (an Orchestration
tool such as Heat can help make this repeatable) and any data populated after
the fact. This allows the new VMs to be backed by a copy-on-write disk image
overlaid on the original base image. The alternative is to :doc:`export and
then import <./vm_snapshot>` snapshots of the VM images. This may require
considerably more disk space as each VM's base image becomes its snapshot,
where previously multiple VMs may have shared the same base image.

Reclaiming Excess Capacity
--------------------------

As workloads are migrated off the previous cloud, compute node hardware can be
freed up to reallocate to the new cloud. Since there is likely no guarantee as
to the order in which users will migrate, it will be necessary to consolidate
the remaining VMs onto a smaller number of machines as utilization drops. This
can be done by performing live migration within the old cloud.

Select a compute node to remove from service and follow the procedure for
:doc:`quiesce_compute`. Once this is done, the node can be removed from the old
cloud and the hardware reused, possibly by adding it to the new cloud.

Adding New Capacity
-------------------

As utilization of the new cloud increases and hardware becomes available from
the old cloud, additional compute nodes can be added to the new cloud with RDO
Manager.

First, register and introspect the additional hardware with Ironic just as you
would have done when :doc:`initially deploying
<../basic_deployment/basic_deployment>` the cloud with RDO Manager. Then
:doc:`scale out <scale_roles>` the 'Compute' role in the new overcloud to start
making use of the additional capacity.
