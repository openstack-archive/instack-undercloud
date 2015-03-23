Install grub2

Normally baremetal images have the bootloader removed because they boot from
PXE-provided kernels and ramdisks, but localboot support requires grub2 to be
installed.  This provides a simple way to do that.
