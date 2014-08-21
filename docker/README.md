Instack Docker Setup
====================

The instack Docker setup provides an environment equivalent to that produced by
running instack-virt-setup in a reuseable Docker container.


Running the instack-virt-setup Docker image
-------------------------------------------

1. Pre-requisites.

        # Run these commands as root
        yum install docker-io qemu-kvm
        modprobe kvm
        modprobe openvswitch
        systemctl start docker

1. Pull the image from the docker registry.

        # Run these commands as root
        # Note that this is about an 8GB download as it contains a fully
        # installed undercloud with all the overcloud images already loaded into
        # glance.
        docker pull slagle/instack-virt

1. Create a directory on your docker host to mount into the container for
   storage. This directory should have at least 30GB free.

        # Run these commands as root
        mkdir -p /storage/docker/lib/instack-virt-environment

1. Start the container. The container must be started with --privileged so that libvirt
   has access to create networks. The host path created in the previous step is
   also mounted into the container at /var/lib/libvirt/images for the instack vm's
   to use for their disks. 

        # Run these commands as root
        setenforce 0
        docker run \
            -it \
            --name instack-virt-environment \
            --privileged \
            --volume /storage/docker/lib/instack-virt-environment:/var/lib/libvirt/images \
            slagle/instack-virt

1. Open a new termainl and look up the IP address of the container

        # Run these commands as root
        docker inspect instack-virt-environment | grep IPAddress

1. ssh as stack to the container's IP address. The initial stack password is also stack.

1. Once ssh'd into the container, start the instack vm

        virsh start instack

   The IP address of the instack vm will be 192.168.122.100.  ssh as the stack
   user (initial password is stack) to the instack vm. It may take a minute or 2 for it to
   come up.

        ssh stack@192.168.122.100

1. Once ssh'd to the instack vm, you must wait for the run of os-collect-config to complete. It should
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
