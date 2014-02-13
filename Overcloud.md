Overcloud
=========

Once the Overcloud has deployed, you can use the devtest instructions to
interact with it. Start off with step 11 from
http://docs.openstack.org/developer/tripleo-incubator/devtest_overcloud.html.

You won't be able to follow the steps exactly. Here's what you need to modify:

* When $TRIPLEO_ROOT is used, replace with /opt/stack instead
* When running setup-neutron, correct subnet ranges will need to be used if
  192.0.2.0/24 is not applicable to the environment.
* When loading the user.qcow2 image into glance, I would use a cirros image
  instead. Download the cirros image from
  https://launchpad.net/cirros/trunk/0.3.0/+download/cirros-0.3.0-x86_64-disk.img
  and specify the path to the downloaded file when you run the glance command.
