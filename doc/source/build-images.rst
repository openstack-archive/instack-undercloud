Building Images
===============

Images must be built prior to doing a deployment. A discovery ramdisk,
deployment ramdisk, and openstack-full image can all be built using
instack-undercloud.

It's recommended to build images on the installed undercloud directly since all
the dependencies are already present.

The following steps can be used to build images. They should be run as the same
non-root user that was used to install the undercloud.

#. Download the RHEL 7.1 cloud image or copy it over from a different
   location, and define the needed environment variable to use the image::

    curl -O http://download.devel.redhat.com/brewroot/packages/rhel-guest-image/7.1/20150203.1/images/rhel-guest-image-7.1-20150203.1.x86_64.qcow2
    export DIB_LOCAL_IMAGE=rhel-guest-image-7.1-20150203.1.x86_64.qcow2

#. Build the 3 image types::

    instack-build-images deploy-ramdisk
    instack-build-images discovery-ramdisk
    instack-build-images overcloud-control
    instack-build-images overcloud-compute

#. Load the images into Glance::

    instack-prepare-for-overcloud
