A ramdisk to do the in-band auto-discovery of the node and auto-register
to Ironic.

* The hardware information collected by the ramdisk are:

  * BMC IP address
  * CPU count and architecture
  * Memory amount in MiB
  * Hard drive size in GiB
  * Mac addresses for all NICs except the loopback

* The ramdisk posts everything to a special endpoint
  {api_version}/discover

The machine is halted at the end of the process.
