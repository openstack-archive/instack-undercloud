Overcloud
=========
This page details how to deploy and use an Overcloud once the Undercloud is
installed.

There are 3 scripts for convenience.

Note that deploy-overcloud can be configured for individual environments via
environment variables. The variables you can set are documented below before
the calls to the script. For their default values, see the deploy-overcloud
script itself.

1. You must source the contents of `tripleo-undercloud-passwords` and `stackrc` into your shell before running the 
   instack-* scripts that interact with the undercloud and overcloud. In order to do that
   you can copy that file to a more convenient location or use sudo to cat the file and copy/paste
   the lines into your shell environment.

1. Run the prepare-for-overcloud script to get setup. This script will
re-downloading images if they already exist in the current working directory.
If you want to force a redownload of the images, delete them first.

        instack-prepare-for-overcloud


1. Edit the deploy-overcloudrc script to set the scaling variable values used to deploy
the overcloud. Set the values to to the number of nodes deployed for each role type. You must deploy
   at least 1 Compute node, but do not need to deploy any block storage or object storage nodes.
   

        COMPUTESCALE=${COMPUTESCALE:-1}
        BLOCKSTORAGESCALE=${BLOCKSTORAGESCALE:-0}
        SWIFTSTORAGESCALE=${SWIFTSTORAGESCALE:-0}

1. Deploy the overcloud using heat:

        # heat
        instack-deploy-overcloud


1. Run the test-overcloud script to launch a Fedora image on the overcloud and
wait until it pings successfully

        instack-test-overcloud
