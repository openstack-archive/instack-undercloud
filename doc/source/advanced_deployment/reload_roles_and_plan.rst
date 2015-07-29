Reload the deployment plan and all deployment roles
===================================================

You may wish to recreate the overcloud deployment plan and deployment roles
from scratch, for example to work with a newer version of the tripleo heat
templates from which the deployment roles are created.

.. note::

    The steps documented below will completely remove the current
    overcloud deployment plan and deployment roles including any overridden
    and saved deployment parameters.

Delete the overcloud deployment plan and any roles
----------------------------------------------------------

Get the current deployment plan uuid and specify it for deletion:

    openstack management plan list

    openstack management plan delete PLAN_UUID

Now you can safely delete all deployment roles:

    roles=`tuskar role-list | grep OpenStack | awk '{print $2}'`

    tuskar-delete-roles --config-file /etc/tuskar/tuskar.conf --uuids $roles

Recreate the deployment roles:
-----------------------------
Roles are reloaded by running the tuskar-db-sync script from the tuskar
tripleo image element:

    /usr/share/tripleo-image-elements/tuskar/os-refresh-config/configure.d/90-tuskar-db-sync

This script defaults to using `/usr/share/openstack-tripleo-heat-templates/`
as the path to the local tripleo heat templates from which to define the roles.
This can be overridden by setting the TUSKAR_ROLE_DIRECTORY environment
variable:

    TUSKAR_ROLE_DIRECTORY=/foo/ /usr/share/tripleo-image-elements/tuskar/os-refresh-config/configure.d/90-tuskar-db-sync

Recreate the deployment plan and associate roles:
----------------------------
Create a new deployment plan and associate the newly created roles to it. This
is achieved by running the plan-add-roles script from the tuskar tripleo image
element:

    /usr/share/tripleo-image-elements/tuskar/os-refresh-config/post-configure.d/101-plan-add-roles


