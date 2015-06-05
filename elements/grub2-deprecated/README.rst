DEPRECATED: Install grub2

Upstream has merged their own grub2 element, so this one will be going away
as soon as all of the dependencies have been updated appropriately.

Normally baremetal images have the bootloader removed because they boot from
PXE-provided kernels and ramdisks, but localboot support requires grub2 to be
installed.  This provides a simple way to do that.
