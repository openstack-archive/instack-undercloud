.. _quiesce_compute:

Quiescing a Compute Node
========================

The process of quiescing a compute node means to migrate workload off the node
so that it can be shut down without affecting the availability of end-users'
VMs. You might want to perform this procedure when rebooting a compute node to
ensure that package updates are applied (e.g. after a kernel update); to
consolidate workload onto a smaller number of machines when scaling down an
overcloud; or when replacing the compute node hardware.

Setting up Keys
---------------

Assuming that the backing files for Nova VMs are not hosted on a shared storage
volume (with all compute nodes having access), the compute nodes will need to
be configured with ssh keys so that the `nova` user on each compute node has
ssh access to the corresponding account on the other compute nodes.

First, generate an ssh key::

    ssh-keygen -t rsa -f nova_id_rsa

Then, on each compute node, run the following script to set up the keys::

    NOVA_SSH=/var/lib/nova/.ssh
    mkdir ${NOVA_SSH}

    cp nova_id_rsa ${NOVA_SSH}/id_rsa
    chmod 600 ${NOVA_SSH}/id_rsa
    cp nova_id_rsa.pub ${NOVA_SSH}/id_rsa.pub
    cp nova_id_rsa.pub ${NOVA_SSH}/authorized_keys

    chown -R nova.nova ${NOVA_SSH}

    # enable login for nova user on compute hosts:
    usermod -s /bin/bash nova

    # add ssh keys of overcloud nodes into known hosts:
    ssh-keyscan -t rsa `os-apply-config --key hosts --type raw --key-default '' | awk '{print $1}'` >>/etc/ssh/ssh_known_hosts


Initiating Migration
--------------------

First, obtain a list of the current Nova services::

    source ~stack/overcloudrc  # admin credentials for the overcloud
    nova service-list

Disable the `nova-compute` service on the node you wish to quiesce, to prevent
new VMs being scheduled on it::

    nova service-disable <service-host> nova-compute


Begin the process of migrating VMs off the node::

    nova host-servers-migrate <service-host>

Completing Migration
--------------------

The current status of the migration process can be retrieved with the command::

    nova migration-list

When migration of each VM completes, its state in Nova will change to
`VERIFY_RESIZE`. This gives you an opportunity to confirm that the migration
completed successfully, or to roll it back. To confirm the migration, use the
command::

    nova resize-confirm <server-name>

Finally, once all migrations are complete and confirmed, remove the service
running (but disabled) on the compute node from Nova altogether::

    nova service-delete <service-id>

You are now free to reboot or shut down the node (using the Ironic API), or
even remove it from the overcloud altogether by scaling down the overcloud
deployment, see :ref:`delete_nodes`.
