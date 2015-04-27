Ready-State (BIOS, RAID)
========================


Dell DRAC Setup
---------------

Configure BIOS based on the deployment profile::

    instack-ironic-deployment --configure-bios

.. note:: The BIOS changes will be applied during the first boot.

Create root RAID volume based on the deployment profile::

    instack-ironic-deployment --configure-root-raid-volume

.. note:: The nodes will be restarted and RAID configuration will happen during
   the first boot.

Discover root block device::

    sudo cp /usr/libexec/os-apply-config/templates/etc/edeploy/state /etc/edeploy/state
    instack-ironic-deployment --discover-nodes

Create non-root RAID volumes based on the deployment profile::

    instack-ironic-deployment --configure-nonroot-raid-volumes

.. note:: The nodes will be restarted and RAID configuration will happen during
   the first boot.
