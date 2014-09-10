Overcloud
=========
This page details how to deploy and use an Overcloud once the Undercloud is
installed.

1. Run the prepare-for-overcloud script to download and load images into glance.
This script will avoid re-downloading images if they already exist in the
current working directory.  If you want to force a redownload of the images,
delete the local images first.

        source tripleo-undercloud-passwords
        source stackrc
        source instack-undercloud/instack-sourcerc
        instack-prepare-for-overcloud

1. Edit the deploy-overcloudrc script to set the scaling variable values used to deploy
the overcloud. Set the values to to the number of nodes deployed for each role type. You must deploy
at least 1 Compute node, but do not need to deploy any block storage or object storage nodes. Once you are done
making any edits to the file, source the file into your shell.
   

        COMPUTESCALE=${COMPUTESCALE:-1}
        BLOCKSTORAGESCALE=${BLOCKSTORAGESCALE:-0}
        SWIFTSTORAGESCALE=${SWIFTSTORAGESCALE:-0}
        source deploy-overcloudrc

1. Deploy the overcloud using heat:

        # heat
        instack-deploy-overcloud


1. Run the test-overcloud script to launch a Fedora image on the overcloud and
wait until it pings successfully

        instack-test-overcloud
