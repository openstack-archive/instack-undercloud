This ramdisk collects hardware information from the machine
it's booted on and posts it to the URL provided via
kernel argument 'ironic_callback_url'.

The ramdisk is meant to be used with Ironic, thus it's name,
but it's not really tied to it. We may switch to talking
to an intermediate service later without changing ramdisk
code.

The hardware information collected by the ramdisk are:

* BMC IP address (may be required for associating with existing node in Ironic)
* CPU count and architecture
* Memory amount in MiB
* Hard drive size in GiB
* Mac addresses for all NICs except the loopback

The machine is halted at the end of the process.
