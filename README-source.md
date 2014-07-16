instack-undercloud via source
=============================

1. Clone this repository and instack

        git clone https://github.com/agroup/instack-undercloud

2. Create and edit your answers file. The descriptions of the parameters that
   can be set are in the sample answers file.

        # Answers file must exist in home directory for now
        # Use either the baremetal or virt sample answers file
        # cp instack-undercloud/instack-baremetal.answers.sample ~/instack.answers
        # cp instack-undercloud/instack-virt.answers.sample ~/instack.answers
        # Perform any answer file edits

3. Source instack-sourcerc and run script to install the undercloud from
   source. The script will produce a lot of output on the sceen. It also logs to
   ~/.instack/install-undercloud.log. You should see `install-undercloud
   Complete!` at the end of a successful run. 
   
   Optionally, export LKG=1 to use the last known good git commits instead of
   master.

        # Optionally use LKG:
        # export LKG=1
        source instack-undercloud/instack-sourcerc
        instack-install-undercloud-source

4. Once the install script has run to completion, you should take note to secure and save the files
   `/root/stackrc` and `/root/tripleo-undercloud-passwords`. Both these files will be needed to interact
   with the installed undercloud. You may copy these files to your home directory to make them 
   easier to source later on, but you should try to keep them as secure and backed up as possible.

That completes the Undercloud install. To proceed with deploying and using the
Overcloud see [Overcloud-packages](Overcloud-packages.md).
