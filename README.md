Undercloud Install via instack
==============================

1. Clone this repository and instack

        git clone https://github.com/agroup/instack-undercloud
        git clone https://github.com/agroup/instack

2. Create and edit your answers file. The descriptions of the parameters that
   can be set are in the sample answers file.

        cd instack-undercloud

        # Use either the baremetal or virt sample answers file
        # cp instack-baremetal.answers.sample instack.answers
        # cp instack-virt.answers.sample instack.answers

        # Return back to directory where instack was cloned
        cd ..

3. Run script to install undercloud. The script will produce a lot of output on
   the sceen. It also logs to ~/.instack/install-undercloud.log. You should see
   `install-undercloud Complete!` at the end of a successful run.

        instack-undercloud/scripts/install-undercloud


That completes the Undercloud install. To proceed with deploying and using the
Overcloud see [Overcloud](Overcloud.md).
