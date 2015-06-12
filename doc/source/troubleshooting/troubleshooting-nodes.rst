Troubleshooting Node Management Failures
========================================

Where Are the Logs?
-------------------

Some logs are stored in *journald*, but most are stored as text files in
``/var/log``.  Ironic and ironic-discoverd logs are stored in journald. Note
that Ironic has 2 units: ``openstack-ironic-api`` and
``openstack-ironic-conductor``. Similarly, ironic-discoverd has
``openstack-ironic-discoverd`` and ``openstack-ironic-discoverd-dnsmasq``.  So
for example to get all ironic-discoverd logs use::

    sudo journalctl -u openstack-ironic-discoverd -u openstack-ironic-discoverd-dnsmasq

If something fails during the discovery ramdisk run, ironic-discoverd
stores the ramdisk logs in ``/var/log/ironic-discoverd/ramdisk/`` as
gz-compressed tar files. File names contain date, time and IPMI address of the
node if it was detected (only for bare metal).

.. _node_registration_problems:

Node Registration Problems
--------------------------

Any problems with node data registered into Ironic can be fixed using the
Ironic CLI.

For example, a wrong MAC can be fixed in two steps:

* Find out the assigned port UUID by running
  ::

    ironic node-port-list <NODE UUID>

* Update the MAC address by running
  ::

    ironic port-update <PORT UUID> replace address=<NEW MAC>

A Wrong IPMI address can be fixed with the following command::

    ironic node-update <NODE UUID> replace driver_info/ipmi_address=<NEW IPMI ADDRESS>


.. _introspection_problems:

Hardware Introspection Problems
--------------------------------

Discovery hangs and times out
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

ironic-discoverd times out discovery process after some time (defaulting to 1
hour) if it never gets response from the discovery ramdisk.  This can be
a sign of a bug in the discovery ramdisk, but usually it happens due to
environment misconfiguration, particularly BIOS boot settings. Please refer to
`ironic-discoverd troubleshooting documentation`_ for information on how to
detect and fix such problems.

Refusing to introspect node with provision state "available"
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you're running discovery directly using ironic-discoverd CLI (or in case of
bugs in our scripts), a node can be in the "AVAILABLE" state, which is meant for
deployment, not for discovery. You should advance node to the "MANAGEABLE" state
before discovery and move it back before deployment.
Please refer to `upstream node states documentation
<https://github.com/openstack/ironic-inspector#node-states>`_ for information
on how to fix it.

How can discovery be stopped?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Currently ironic-discoverd does not provide means for stopping discovery. The
recommended path is to wait until it times out. Changing ``timeout`` setting
in ``/etc/ironic-discoverd/discoverd.conf`` may be used to reduce this timeout
from 1 hour (which usually too much, especially on virtual environment).

If you do need to stop discovery **for all nodes** right now, do the
following for each node::

    ironic node-set-power-state UUID off

then remove ironic-discoverd cache and restart it::

    rm /var/lib/ironic-discoverd/discoverd.sqlite
    sudo systemctl restart openstack-ironic-discoverd


.. _ironic-discoverd troubleshooting documentation: https://github.com/openstack/ironic-inspector#troubleshooting
