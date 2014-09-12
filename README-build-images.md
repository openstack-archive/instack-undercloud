Overcloud image building
========================
    
1. Create initial directory for instack, and clone the needed repositories.


         mkdir instack
         cd instack
         git clone https://github.com/agroup/instack-undercloud

1. Setup needed checkouts. If you don't want to use Delorean packages, or the
last known good commits (use latest from trunk), then set those environment
variables to 0. Exporting RUN_INSTACK=0 will create the initial
checkouts. Note however that some pip dependencies will still be installed on
the machine.

        # If you don't want to use Delorean...
        # export DELOREAN=0
        # If you don't want to use the last known good commits...
        # export LKG=0

        source instack-undercloud/instack-sourcerc
        export RUN_INSTACK=0
        instack-install-undercloud-source

2. Run script to build images. This will create any Overcloud images and
deployment images that don't already exist in the current directory. If you
only need to rebuild a single image, make sure the other images already exist
in the current directory.

        instack-build-images
