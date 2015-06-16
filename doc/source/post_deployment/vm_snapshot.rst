Import/Export of VM Snapshots
=============================

Create a snapshot of a running server
-------------------------------------
Create a new image by taking a snapshot of a running server and download the
image.

  ::

      nova image-create instance_name image_name
      glance image-download image_name --file exported_vm.qcow2

Import an image into Overcloud and launch an instance
-----------------------------------------------------
Upload the exported image into glance in Overcloud and launch a new instance.

  ::

      glance image-create --name imported_image --file exported_vm.qcow2 --disk-format qcow2 --container-format bare
      nova boot --poll --key-name default --flavor m1.demo --image imported_image --nic net-id=net_id imported

.. note::
   **Warning**: disadvantage of using glance image for export/import VMs is
   that each VM disk has to be copied in and out into glance in source and
   target clouds. Also by making snapshot qcow layering system is lost.
