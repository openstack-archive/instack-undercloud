Ready-State (BIOS, RAID)
========================

Start with matching the nodes to profiles as described in
:doc:`profile_matching`.

Then trigger the BIOS and RAID configuration based on the deployment profile::

    instack-ironic-deployment --configure-nodes
