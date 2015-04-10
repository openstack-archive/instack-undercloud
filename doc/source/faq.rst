Frequently Asked Questions
==========================

Discovery times out
~~~~~~~~~~~~~~~~~~~

ironic-discoverd times out discovery process after some time (defaulting to 1
hour) if it never gets response from the discovery ramdisk.  This can be
a sign of a bug in the discovery ramdisk, but usually it happens due to
environment misconfiguration, particularly BIOS boot settings. Please refer to
`ironic-discoverd troubleshooting documentation`_ for information on how to
detect and fix such problems.


.. _ironic-discoverd troubleshooting documentation: https://github.com/stackforge/ironic-discoverd#troubleshooting
