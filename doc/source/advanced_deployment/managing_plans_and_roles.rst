Managing Plans and Roles
========================

This section provides a description of the Plan and Role concepts and the
operations available to each from the command line.

To learn how to delete and reload all plans and roles skip to the relevant
`Reload the deployment plan and all deployment roles`_ section below.

Understanding Roles & Plans
---------------------------

Roles represent the functionality that will be served by a node, for example a
Compute or Storage node. Plans define the full deployment and consist of one
or more roles and their related Parameters.


Roles
-----

The Roles included in the Tuskar API can be viewed with the following command::

    $ openstack management role list
    +--------------------------------------+----------------+---------+---------------------------------------------------+
    | uuid                                 | name           | version | description                                       |
    +--------------------------------------+----------------+---------+---------------------------------------------------+
    | 6830e747-6d43-44bf-99b6-97a7145c58c6 | Swift-Storage  |       1 | OpenStack swift storage node configured by Puppet |
    | 96faca30-8c05-48b2-b9c8-d01cd2d0dc47 | Compute        |       1 | OpenStack hypervisor node configured via Puppet.  |
    | b0c87438-871d-46e2-9fee-4b42c65f3c45 | Ceph-Storage   |       1 | OpenStack ceph storage node configured by Puppet  |
    | d5ffd638-8df3-4ed6-8925-32e8891dae25 | Cinder-Storage |       1 | OpenStack cinder storage configured by Puppet     |
    | e3e09fa8-00c8-4870-8f2b-de67a9faa5ab | Controller     |       1 | OpenStack controller node configured by Puppet.   |
    +--------------------------------------+----------------+---------+---------------------------------------------------+


Plans
-----

By default Tuskar comes with one Plan named overcloud with all of the above
Roles added to the plan. However, only Control and Compute have their scale
value set and will be deployed by default.

The Plan can be viewed with the following command::

    $ openstack management plan list
    +--------------------------------------+-----------+-------------+------------------------------------------------------------------+
    | uuid                                 | name      | description | roles                                                            |
    +--------------------------------------+-----------+-------------+------------------------------------------------------------------+
    | eac9c4cc-9d85-4c6a-85bb-e1f38afcff7e | overcloud | None        | Compute, Ceph-Storage, Cinder-Storage, Controller, Swift-Storage |
    +--------------------------------------+-----------+-------------+------------------------------------------------------------------+

Once you have the Plan UUID you can view more details about the plan::

    $ openstack management plan show eac9c4cc-9d85-4c6a-85bb-e1f38afcff7e
    +-------------+------------------------------------------------------------------+
    | Field       | Value                                                            |
    +-------------+------------------------------------------------------------------+
    | created_at  | 2015-07-13T10:09:14                                              |
    | description | None                                                             |
    | name        | overcloud                                                        |
    | parameters  | Parameter output suppressed. Use --long to display them.         |
    | roles       | Compute, Ceph-Storage, Cinder-Storage, Controller, Swift-Storage |
    | updated_at  | None                                                             |
    | uuid        | eac9c4cc-9d85-4c6a-85bb-e1f38afcff7e                             |
    +-------------+------------------------------------------------------------------+

The command can be repeated with ``--long`` appended to the end for a
detailed output of all the available Plan parameters.


Adding and Removing Roles
~~~~~~~~~~~~~~~~~~~~~~~~~

Roles can be removed from the plan like this::

    $ openstack management plan remove role "[plan-uuid]" "[role-uuid]"

And similarly they can be added back to the plan::

    $ openstack management plan add role "[plan-uuid]" "[role-uuid]"

The output of both of these commands is the summary of the plan and it will
reflect the role being added or removed.


Assigning Flavors to Roles
~~~~~~~~~~~~~~~~~~~~~~~~~~

Roles can have a flavor assigned with the following command::

    $ openstack management plan set "[plan-uuid]" -F Compute-1=baremetal

In this example we are assigning the ``baremetal`` flavor to the Compute role,
but we need to include the role version when doing this. Making the syntax
``-F [role-name]-[role-version]=[flavor-name]``.


Setting Scale values
~~~~~~~~~~~~~~~~~~~~

Similar to assigning Flavors, scaling an individual role can be done like
this::

    $ openstack management plan set "[plan-uuid]" -S Compute-1=3

In this example we are scaling the Compute role to three nodes.


Setting other parameters
~~~~~~~~~~~~~~~~~~~~~~~~

Arbitrary parameters can be set for Roles. To do this, the following syntax
needs to be used.::

    $ openstack management plan set "[plan-uuid]" -P Compute-1::Image=compute

Making the syntax ``-F [role-name]-[role-version]::[parameter-
name]=[value]``. The above example assigns the compute image to the compute
role - for this to work a compute image needs to be uploaded to glance.


Downloading a Plan
------------------

Plans can be downloaded from Tuskar. The result of doing this is a set of
Heat templates that can be then manipulated or manually passed to the Heat
client.::

    $ openstack management plan download "[plan-uuid]" -O path/to/output

Once you have downloaded the templates from Tuskar, they can be sent directly
to Heat with this command.::

    $ heat stack-create overcloud \
        -f path/to/output/plan.yaml \
        -e path/to/output/environment.yaml \
        -t 240;

Reload the deployment plan and all deployment roles
---------------------------------------------------

You may wish to recreate the overcloud deployment plan and deployment roles
from scratch, for example to work with a newer version of the tripleo heat
templates from which the deployment roles are created.

.. note::

    The steps documented below will completely remove the current
    overcloud deployment plan and deployment roles including any overridden
    and saved deployment parameters.

Delete the overcloud deployment plan and any roles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get the current deployment plan uuid and specify it for deletion::

    openstack management plan list

    openstack management plan delete PLAN_UUID

Now you can safely delete all deployment roles::

    roles=`tuskar role-list | grep OpenStack | awk '{print $2}'`

    tuskar-delete-roles --config-file /etc/tuskar/tuskar.conf --uuids $roles

Recreate the deployment roles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Roles are reloaded by running the tuskar-db-sync script from the tuskar
tripleo image element::

    /usr/share/tripleo-image-elements/tuskar/os-refresh-config/configure.d/90-tuskar-db-sync

This script defaults to using `/usr/share/openstack-tripleo-heat-templates/`
as the path to the local tripleo heat templates from which to define the roles.
This can be overridden by setting the TUSKAR_ROLE_DIRECTORY environment
variable::

    TUSKAR_ROLE_DIRECTORY=/foo/ /usr/share/tripleo-image-elements/tuskar/os-refresh-config/configure.d/90-tuskar-db-sync

Recreate the deployment plan and associate the new roles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Create a new deployment plan and associate the newly created roles to it. This
is achieved by running the plan-add-roles script from the tuskar tripleo image
element::

    /usr/share/tripleo-image-elements/tuskar/os-refresh-config/post-configure.d/101-plan-add-roles


