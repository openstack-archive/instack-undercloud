Instack Docker Setup
====================

The instack Docker setup provides an environment equivalent to that produced by
running instack-virt-setup in a reuseable Docker container.


Running the instack-virt-setup Docker image
-------------------------------------------

1. Pull the image from the docker registry.

        docker pull slagle/instack-virt

1. Create a directory on your docker host to mount into the container for
   storage. This directory should have at least 30GB free.

        mkdir -p /storage/docker/lib/instack-virt-environment

1. Start the container. The container must be started with --privileged so that libvirt
   has access to create networks. The host path created in the previous step is
   also mounted into the container at /var/lib/libvirt/images for the instack vm's
   to use for their disks. 

        docker run \
            -it \
            --name instack-virt-environment \
            --privileged \
            --volume /storage/docker/lib/instack-virt-environment:/var/lib/libvirt/images \
            slagle/instack-virt

1. Look up the IP address of the container

        docker inspect instack-virt-environment | grep IPAddress

1. ssh as stack to the container's IP address. The initial stack password is also stack.

1. Start the instack vm

        virsh start instack

   The IP address of the instack vm will be 192.168.122.100.  ssh as the stack
   user (initial password is stack) to the vm. It may take a minute or 2 for it to
   come up.

        ssh stack@192.168.122.100

1. You must wait for the run of os-collect-config to complete. It should
   complete in < 5 minutes. Use the following command to check for completion.

        sudo journalctl -u os-collect-config --full -f | grep "Completed phase migration"

1. Once os-collect-config has comleted, you can source the necessary files and
   verify the images are already loaded in glance. Note that you must source
   the 3 files below anytime you want to use the OpenStack clients. The paths
   are relative to /home/stack.

        source instack-undercloud/instack-sourcerc
        source tripleo-undercloud-passwords
        source stackrc
        glance image-list

Building the instack-virt-setup Docker image
--------------------------------------------
There is no reason to build the Docker image yourself if you pulled it
following the commands above. These steps are here just to document the build
process.

Building the docker image is a multi-step process. There is a Dockerfile to
assist with building the initial image. 

1. Run through instack-virt-setup on the build host, start the instack vm,
   install the undercloud, load the images into glance. shutdown the instack
   vm.

1. After the instack vm is started, ssh to the vm and create the answers file
   and deploy-virt-overcloudrc underneath /home/stack. Be sure to populate
   $MACS in deploy-virt-overcloudrc with the actual values of the baremetal vm
   nodes as created from instack-virt-setup.

1. Poweroff the instack vm.

1. Run the rest of the commands here as root

1. Clone this git repository, switch to the docker branch, and cd to the docker
   build directory.

        git clone https://github.com/agroup/instack-undercloud
        cd instack-undercloud
        git checkout docker
        cd docker/instack-virt

1. Copy needed files from the build host into the build directory.

        cp /var/lib/libvirt/images/instack.qcow2 .
        cp /etc/libvirt/qemu/baremetal_0.xml .
        cp /etc/libvirt/qemu/baremetal_1.xml .
        cp /etc/libvirt/qemu/baremetal_2.xml .
        cp /etc/libvirt/qemu/baremetal_3.xml .
        cp /etc/libvirt/qemu/instack.xml .
        cp /etc/libvirt/qemu/networks/default.xml .
        cp /etc/libvirt/qemu/networks/brbm.xml .
        cp /home/stack/.ssh/id_rsa_virt_power* .

1. Update the vm xml definitions to remove the selinux relabel command

        sed -i '/selinux/d' instack.xml baremetal_*.xml
        
1. View instack.xml and get the mac address of the default network interface.

1. Edit default.xml and add the following line in the `<dhcp>` stanza. Replace
   the value for mac with the mac address you got in the previous step.

        <host mac='52:54:00:e1:f3:7e' name='instack' ip='192.168.122.100'/>

1. Sparsify instack.qcow2

        virt-sparsify instack.qcow2 instack.qcow2.new
        mv instack.qcow2.new instack.qcow2
        
1. Pull the Fedora base image and then build the docker image

        docker pull fedora
        docker build -t instack-virt .

1. Optionally tag and push the image.
