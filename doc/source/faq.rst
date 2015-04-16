Frequently Asked Questions
==========================

Where are the logs?
~~~~~~~~~~~~~~~~~~~

Some logs are stored in *journald*, but most are stored as text files in
``/var/log``.  Ironic and ironic-discoverd logs are stored in journald. Note
that Ironic has 2 units: ``openstack-ironic-api`` and
``openstack-ironic-conductor``. Similarly, ironic-discoverd has
``openstack-ironic-discoverd`` and ``openstack-ironic-discoverd-dnsmasq``.  So
for example to get all ironic-discoverd logs use::

    sudo journalctl -u openstack-ironic-discoverd -u openstack-ironic-discoverd-dnsmasq

Discovery FAQ
~~~~~~~~~~~~~

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
before discovery and move it back before deployment. While our scripts
generally do it, they suffer from `bug 1212134
<https://bugzilla.redhat.com/show_bug.cgi?id=1212134>`_ which may cause nodes
to be in the wrong state. Please refer to `upstream node states documentation
<https://github.com/stackforge/ironic-discoverd#node-states>`_ for information
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


.. _ironic-discoverd troubleshooting documentation: https://github.com/stackforge/ironic-discoverd#troubleshooting
