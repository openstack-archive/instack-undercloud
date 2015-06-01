Ready-State (BIOS, RAID)
========================

Match deployment profiles
-------------------------
Before doing the ready-state configuration, we first must match the nodes to profiles.

  ::

      sudo yum install -y ahc-tools
      sudo -E ahc-match

Ready-state configuration
-------------------------

Trigger the BIOS and RAID configuration based on the deployment profile::

    instack-ironic-deployment --configure-nodes
