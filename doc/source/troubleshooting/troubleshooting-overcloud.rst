Troubleshooting a Failed Overcloud Deployment
=============================================

If an Overcloud deployment has failed, the OpenStack clients and service log
files can be used to troubleshoot the failed deployment. The following commands
are all run on the Undercloud and assume a stackrc file has been sourced.

Identifying Failed Component
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In most cases, Heat will show the failed overcloud stack when a deployment
has failed::

 $ heat stack-list

 +--------------------------------------+------------+--------------------+----------------------+
 | id                                   | stack_name | stack_status       | creation_time        |
 +--------------------------------------+------------+--------------------+----------------------+
 | 7e88af95-535c-4a55-b78d-2c3d9850d854 | overcloud  | CREATE_FAILED      | 2015-04-06T17:57:16Z |
 +--------------------------------------+------------+--------------------+----------------------+

Occassionally, Heat is not even able to create the the stack, so the ``heat
stack-list`` output will be empty. If this is the case, observe the message
that was printed to the terminal when ``instack-deploy-overcloud`` or ``heat
stack-create`` was run.

Next, there are a few layers on which the deployment can fail:

* Orchestration (Heat and Nova services)
* Bare metal provisioning (Ironic service)
* Post-deploy configuration (Puppet)

As Ironic service is in the middle layer, you can use its shell to guess the
failed layer. Issue ``ironic node-list`` command to see all registered nodes
and their current status, you will see something like::

    +--------------------------------------+------+---------------+-------------+-----------------+-------------+
    | UUID                                 | Name | Instance UUID | Power State | Provision State | Maintenance |
    +--------------------------------------+------+---------------+-------------+-----------------+-------------+
    | f1e26112-5fbd-4fc4-9612-ecce7a1d86aa | None | None          | power off   | available       | False       |
    | f0b8c105-f1d7-4059-a9a3-b050c3340340 | None | None          | power off   | available       | False       |
    +--------------------------------------+------+---------------+-------------+-----------------+-------------+

Pay close attention to **Provision State** and **Maintenance** columns
in the resulting table.

* If the command shows empty table or less nodes that you expect, or
  **Maintenance** is ``True``, or **Provision State** is ``manageable``,
  there was a problem during node enrolling and introspection.
  Please go back to these steps.

  For example, **Maintenance** goes to ``True`` automatically, if wrong power
  credentials are provided.

* If **Provision State** is ``available`` then the problem occured before
  bare metal deployment has even started. Proceed with `Debugging Using Heat`_.

* If **Provision State** is ``active`` and **Power State** is ``power on``,
  then bare metal deployment has finished successfully, and problem happened
  during the post-deployment configuration step. Again, refer to `Debugging
  Using Heat`_.

* If **Provision State** is ``wait call-back``, then bare metal deployment is
  not finished for this node yet. You may want to wait until the status
  changes.

* If **Provision State** is ``error`` or ``deploy failed``, then bare metal
  deployment has failed for this node. Issue
  ::

    ironic node-show <UUID>

  and look for **last_error** field. It will contain error description.

  If the error message is vague, you can use logs to clarify it::

    sudo journalctl -u openstack-ironic-conductor -u openstack-ironic-api

  If you see wait timeout error, and node **Power State** is ``power on``,
  then try to connect to the virtual console of the failed machine. Use
  ``virt-manager`` tool for virtual machines and vendor-specific virtual
  console (e.g. iDRAC for DELL) for bare metal machines.

Debugging Using Heat
~~~~~~~~~~~~~~~~~~~~

* Identifying the failed Heat resource

  List all the stack resources to see which one failed.

  ::

    $ heat resource-list overcloud

    +-----------------------------------+-----------------------------------------------+---------------------------------------------------+-----------------+----------------------+
    | resource_name                     | physical_resource_id                          | resource_type                                     | resource_status | updated_time         |
    +-----------------------------------+-----------------------------------------------+---------------------------------------------------+-----------------+----------------------+
    | BlockStorage                      | 9e40a1ee-96d3-4920-868d-683d3788e129          | OS::Heat::ResourceGroup                           | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | BlockStorageAllNodesDeployment    | 2c453f6b-7378-44c8-a0ad-57de57d9c57f          | OS::Heat::StructuredDeployments                   | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | BlockStorageNodesPostDeployment   |                                               | OS::TripleO::BlockStoragePostDeployment           | INIT_COMPLETE   | 2015-04-06T21:15:20Z |
    | CephClusterConfig                 | 1684e7a3-0e42-44fe-9db4-7543b742fbfc          | OS::TripleO::CephClusterConfig::SoftwareConfig    | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | CephStorage                       | 48b3460c-bf9a-4663-99fc-2b4fa01b8dc1          | OS::Heat::ResourceGroup                           | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | CephStorageAllNodesDeployment     | 76beb3a9-8327-4d2e-a206-efe12f1613fb          | OS::Heat::StructuredDeployments                   | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | CephStorageCephDeployment         | af8fb02a-5bc6-468c-8fac-fbe7e5b2c689          | OS::Heat::StructuredDeployments                   | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | CephStorageNodesPostDeployment    |                                               | OS::TripleO::CephStoragePostDeployment            | INIT_COMPLETE   | 2015-04-06T21:15:20Z |
    | Compute                           | e5e6ec84-197f-4bf6-b8ac-eb11fe494cdf          | OS::Heat::ResourceGroup                           | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | ComputeAllNodesDeployment         | e6d44fbf-9683-4765-acbb-4a3d31c8fd48          | OS::Heat::StructuredDeployments                   | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | ControllerNodesPostDeployment     | e551e472-f2db-4468-b586-0374678d71a3          | OS::TripleO::ControllerPostDeployment             | CREATE_FAILED   | 2015-04-06T21:15:20Z |
    | ComputeCephDeployment             | 673608d5-70d7-453a-ac78-7987bc2c0158          | OS::Heat::StructuredDeployments                   | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | ComputeNodesPostDeployment        | 1078e3e3-9f6f-48b9-8961-a30f44098856          | OS::TripleO::ComputePostDeployment                | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | ControlVirtualIP                  | 6402b396-84aa-4cf6-9849-305205755604          | OS::Neutron::Port                                 | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | Controller                        | ffc45352-9708-486d-81ac-3b60efa8e8b8          | OS::Heat::ResourceGroup                           | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | ControllerAllNodesDeployment      | f73c6e33-3dd2-46f1-9eca-0d2981a4a986          | OS::Heat::StructuredDeployments                   | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | ControllerBootstrapNodeConfig     | 01ce5b6a-794a-4828-bad9-49d5fbfd55bf          | OS::TripleO::BootstrapNode::SoftwareConfig        | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | ControllerBootstrapNodeDeployment | c963d53d-879b-4a41-a10a-9000ac9f02a1          | OS::Heat::StructuredDeployments                   | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | ControllerCephDeployment          | 2d4281df-31ea-4433-820d-984a6dca6eb1          | OS::Heat::StructuredDeployments                   | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | ControllerClusterConfig           | 719c0d30-a4b8-4f77-9ab6-b3c9759abeb3          | OS::Heat::StructuredConfig                        | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | ControllerClusterDeployment       | d929aa40-1b73-429e-81d5-aaf966fa6756          | OS::Heat::StructuredDeployments                   | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | ControllerSwiftDeployment         | cf28f9fe-025d-4eed-b3e5-3a5284a2aa60          | OS::Heat::StructuredDeployments                   | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | HeatAuthEncryptionKey             | overcloud-HeatAuthEncryptionKey-5uw6wo7kavnq  | OS::Heat::RandomString                            | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | MysqlClusterUniquePart            | overcloud-MysqlClusterUniquePart-vazyj2s4n2o5 | OS::Heat::RandomString                            | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | MysqlRootPassword                 | overcloud-MysqlRootPassword-nek2iky7zfdm      | OS::Heat::RandomString                            | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | ObjectStorage                     | 47327c98-533e-4cc2-b1f3-d8d0eedba822          | OS::Heat::ResourceGroup                           | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | ObjectStorageAllNodesDeployment   | 7bb691aa-fa93-4f10-833e-6edeccc61408          | OS::Heat::StructuredDeployments                   | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | ObjectStorageNodesPostDeployment  | d4d16f39-384a-4d6a-9719-1dd9b2d4ff09          | OS::TripleO::ObjectStoragePostDeployment          | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | ObjectStorageSwiftDeployment      | afc87385-8b40-4097-b529-2a5bc81c94c8          | OS::Heat::StructuredDeployments                   | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | PublicVirtualIP                   | 4dd92878-8f29-49d8-9d3d-bc0cd44d26a9          | OS::Neutron::Port                                 | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | RabbitCookie                      | overcloud-RabbitCookie-uthzbos3l66v           | OS::Heat::RandomString                            | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | SwiftDevicesAndProxyConfig        | e2141170-bb77-4509-b8bd-58447b2cd15f          | OS::TripleO::SwiftDevicesAndProxy::SoftwareConfig | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    | allNodesConfig                    | cbd42692-fffa-4527-a519-bd4014ebf0fb          | OS::TripleO::AllNodes::SoftwareConfig             | CREATE_COMPLETE | 2015-04-06T21:15:20Z |
    +-----------------------------------+-----------------------------------------------+---------------------------------------------------+-----------------+----------------------+

  In this example, notice how the **ControllerNodesPostDeployment** resource
  has failed. The **\*PostDeployment** resources are the configuration that is
  applied to the deployed Overcloud nodes. When these resources have failed it
  indicates that something went wrong during the Overcloud node configuration,
  perhaps when Puppet was run.

* Show the failed resource

  ::

    $ heat resource-show overcloud ControllerNodesPostDeployment

    +------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Property               | Value                                                                                                                                                               |
    +------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | attributes             | {}                                                                                                                                                                  |
    | description            |                                                                                                                                                                     |
    | links                  | http://192.0.2.1:8004/v1/cea2a0c78d2447bc9a0f7caa35c9224c/stacks/overcloud/ec3e3251-f949-4df9-92be-dbd37c6992a1/resources/ControllerNodesPostDeployment (self)      |
    |                        | http://192.0.2.1:8004/v1/cea2a0c78d2447bc9a0f7caa35c9224c/stacks/overcloud/ec3e3251-f949-4df9-92be-dbd37c6992a1 (stack)                                             |
    |                        | http://192.0.2.1:8004/v1/cea2a0c78d2447bc9a0f7caa35c9224c/stacks/overcloud-ControllerNodesPostDeployment-6kcqm5zuymqu/e551e472-f2db-4468-b586-0374678d71a3 (nested) |
    | logical_resource_id    | ControllerNodesPostDeployment                                                                                                                                       |
    | physical_resource_id   | e551e472-f2db-4468-b586-0374678d71a3                                                                                                                                |
    | required_by            | BlockStorageNodesPostDeployment                                                                                                                                     |
    |                        | CephStorageNodesPostDeployment                                                                                                                                      |
    | resource_name          | ControllerNodesPostDeployment                                                                                                                                       |
    | resource_status        | CREATE_FAILED                                                                                                                                                       |
    | resource_status_reason | ResourceUnknownStatus: Resource failed - Unknown status FAILED due to "None"                                                                                        |
    | resource_type          | OS::TripleO::ControllerPostDeployment                                                                                                                               |
    | updated_time           | 2015-04-06T21:15:20Z                                                                                                                                                |
    +------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------+

  The ``resource-show`` doesn't always show a clear reason why the resource
  failed. In these cases, logging into the Overcloud node is required to
  further troubleshoot the issue.

* Logging into Overcloud nodes

  Use the nova client to see the IP addresses of the Overcloud nodes.

  ::

    $ nova list

    +--------------------------------------+-------------------------------------------------------+--------+------------+-------------+---------------------+
    | ID                                   | Name                                                  | Status | Task State | Power State | Networks            |
    +--------------------------------------+-------------------------------------------------------+--------+------------+-------------+---------------------+
    | 18014b02-b143-4ca2-aeb9-5553bec93cff | ov-4tvbtgpv7w-0-soqocxy2w4fr-NovaCompute-nlrxd3lgmmlt | ACTIVE | -          | Running     | ctlplane=192.0.2.13 |
    | 96a57a46-1e48-4c66-adaa-342ee4e98972 | ov-rf4hby6sblk-0-iso3zlqmyzfe-Controller-xm2imjkzalhi | ACTIVE | -          | Running     | ctlplane=192.0.2.14 |
    +--------------------------------------+-------------------------------------------------------+--------+------------+-------------+---------------------+

  Login as the ``heat-admin`` user to one of the deployed nodes. In this
  example, since the **ControllerNodesPostDeployment** resource failed, login
  to the controller node. The ``heat-admin`` user has sudo access.

  ::

    $ ssh heat-admin@192.0.2.14

  While logged in to the controller node, examine the log for the
  ``os-collect-config`` log for a possible reason for the failure.

  ::

    $ sudo journalctl -u os-collect-config

* Failed Nova Server ResourceGroup Deployments

  In some cases, Nova fails deploying the node in entirety. This situation
  would be indicated by a failed ``OS::Heat::ResourceGroup`` for one of the
  Overcloud role types such as Control or Compute.

  Use nova to see the failure in this case.

  ::

    $ nova list
    $ nova show <server-id>

  The most common error shown will reference the error message ``No valid host
  was found``. Refer to `No Valid Host Found Error`_ below.

  In other cases, look at the following log files for further troubleshooting::

    /var/log/nova/*
    /var/log/heat/*
    /var/log/ironic/*

* Using SOS

  SOS is a set of tools that gathers information about system hardware and
  configuration. The information can then be used for diagnostic purposes and
  debugging. SOS is commonly used to help support technicians and developers.

  SOS is useful on both the undercloud and overcloud. Install the ``sos``
  package and then generate a report::

    $ sudo sosreport --all-logs

No Valid Host Found Error
~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes ``/var/log/nova/nova-conductor.log`` contains the following error::

    NoValidHost: No valid host was found. There are not enough hosts available.

"No valid host was found" means that the Nova Scheduler could not find a bare
metal node suitable for booting the new instance.

This in turn usually means some mismatch between resources that Nova expects
to find and resources that Ironic advertised to Nova.

A few things should be checked in this case:

#. Introspection should have succeeded for you before, or you should have
   entered the required Ironic node properties manually.
   For each node in ``ironic node-list`` use
   ::

    ironic node-show <IRONIC-NODE-UUID>

   and make sure that ``properties`` JSON field has valid values for keys
   ``cpus``, ``cpu_arch``, ``memory_mb`` and ``local_gb``.

#. Nova flavor that you are using does not exceed the Ironic node properties
   above for a required number of nodes. Use
   ::

    nova flavor-show <FLAVOR NAME>

   to compare.

#. Make sure that enough nodes are in ``available`` state according to
   ``ironic node-list``. Nodes in ``manageable`` state usually mean they
   have failed introspection.

#. Make sure nodes you're going to deploy to are not in maintenance mode.
   Again, use ``ironic node-list`` to check. A node automatically going to
   maintenance mode usually means wrong power credentials for this node. Check
   them and then remove maintenance mode::

    ironic node-set-maintenance <IRONIC-NODE-UUID> off

#. If you're using advanced profile matching with multiple flavors, make sure
   you have enough nodes corresponding to each flavor/profile. Watch
   ``capabilities`` key in ``properties`` field for ``ironic node-show``.
   It should contain e.g. ``profile:compute``.

#. It takes some time for nodes information to propagate from Ironic to Nova
   after introspection. Our tooling usually accounts for it, but if you did
   some steps manually, there may be a period of time when nodes are not
   available to Nova yet. Check that
   ::

    nova hypervisor-stats

   correctly shows total amount of resources in your system.
