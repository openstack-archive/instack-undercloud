Ready-State (BIOS, RAID)
========================

.. note:: Ready-state configuration currently works only with Dell DRAC
          machines.

Ready-state configuration can be used to prepare bare-metal resources for
deployment. It includes BIOS and RAID configuration based on a predefined
profile.

To define the target BIOS and RAID configuration for a deployment profile, you
need to create a JSON-like ``<profile>.cmdb`` file in
``/etc/ahc-tools/edeploy``. The configuration will be applied only to nodes
that match the ``<profile>.specs`` rules.


Define the target BIOS configuration
------------------------------------

To define a BIOS setting, list the name of the setting and its target
value::

    [
        {
            'bios_settings': {'ProcVirtualization': 'Enabled'}
        }
    ]


Define the target RAID configuration
------------------------------------

The RAID configuration can be defined in 2 ways: either by listing the IDs
of the physical disks, or letting Ironic assign physical disks to the
RAID volume.

By providing a list of physical disk IDs the following attributes are required:
``controller``, ``size_gb``, ``raid_level`` and the list of ``physical_disks``.
``controller`` should be the FQDD of the RAID controller assigned by the DRAC
card. Similarly, the list of ``physical_disks`` should be the FQDDs of physical
disks assigned by the DRAC card. An example::

    [
        {
            'logical_disks': [
                {'controller': 'RAID.Integrated.1-1',
                 'size_gb': 100,
                 'physical_disks': [
                     'Disk.Bay.0:Enclosure.Internal.0-1:RAID.Integrated.1-1',
                     'Disk.Bay.1:Enclosure.Internal.0-1:RAID.Integrated.1-1',
                     'Disk.Bay.2:Enclosure.Internal.0-1:RAID.Integrated.1-1'],
                 'raid_level': '5'},
            ]
        }
    ]

By letting Ironic assign physical disks to the RAID volume, the following
attributes are required: ``controller``, ``size_gb``, ``raid_level`` and the
``number_of_physical_disks``. ``controller`` should be the FQDD of the RAID
controller assigned by the DRAC card. An example::

    [
        {
            'logical_disks': [
                {'controller': 'RAID.Integrated.1-1',
                 'size_gb': 50,
                 'raid_level': '1',
                 'number_of_physical_disks': 2},
            ]
        }
    ]


Complete example for a ``control.cmdb``
---------------------------------------
::

    [
        {
            'bios_settings': {'ProcVirtualization': 'Enabled'},
            'logical_disks': [
                {'controller': 'RAID.Integrated.1-1',
                 'size_gb': 50,
                 'raid_level': '1',
                 'number_of_physical_disks': 2,
                 'disk_type': 'hdd',
                 'interface_type': 'sas',
                 'volume_name': 'root_volume',
                 'is_root_volume': True},
                {'controller': 'RAID.Integrated.1-1',
                 'size_gb': 100,
                 'physical_disks': [
                    'Disk.Bay.0:Enclosure.Internal.0-1:RAID.Integrated.1-1',
                    'Disk.Bay.1:Enclosure.Internal.0-1:RAID.Integrated.1-1',
                    'Disk.Bay.2:Enclosure.Internal.0-1:RAID.Integrated.1-1'],
                 'raid_level': '5',
                 'volume_name': 'data_volume1'}
            ]
        }
    ]


Trigger the ready-state configuration
-------------------------------------

Continue with matching the nodes to profiles as described in
:doc:`profile_matching`.

Then trigger the BIOS and RAID configuration based on the matched deployment
profile::

    instack-ironic-deployment --configure-nodes
