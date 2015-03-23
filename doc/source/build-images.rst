Building Images
===============

Images must be built prior to doing a deployment. A discovery ramdisk,
deployment ramdisk, and openstack-full image can all be built using
instack-undercloud.

It's recommended to build images on the installed undercloud directly since all
the dependencies are already present.

The following steps can be used to build images. They should be run as the same
non-root user that was used to install the undercloud.

#. The built images will automatically have the same base OS as the running
   undercloud. See the Note below to choose a different OS::

  .. note:: To build images with a base OS different from the undercloud,
     set the ``$NODE_DIST`` environment variable prior to running
     ``instack-build-images``:

     .. admonition:: CentOS
        :class: centos-tag

        ::

            export NODE_DIST=centos7

     .. admonition:: RHEL
        :class: rhel-tag

        ::

            export NODE_DIST=rhel7

2. Build the required images:

   .. admonition:: RHEL
      :class: rhel-tag

      Download the RHEL 7.1 cloud image or copy it over from a different location,
      and define the needed environment variable for RHEL 7.1 prior to running
      ``instack-build-images``::

          curl -O http://download.devel.redhat.com/brewroot/packages/rhel-guest-image/7.1/20150203.1/images/rhel-guest-image-7.1-20150203.1.x86_64.qcow2
          export DIB_LOCAL_IMAGE=rhel-guest-image-7.1-20150203.1.x86_64.qcow2

   ::
  
      instack-build-images

#. Load the images into Glance::

    instack-prepare-for-overcloud
