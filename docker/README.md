Instack Docker Setup
====================

The instack Docker setup provides an environment equivalent to that produced by
running instack-virt-setup in a reuseable Docker container.


Running the instack-virt-setup Docker image
-------------------------------------------

Pull the image from the docker registry.

        docker pull slagle/instack-virt-setup

Run the image. The container must be started with --privileged so that libvirt
has access to create networks. A host path must also be mounted into the
container at /var/lib/libvirt/images for the instack vm's to use for their
disks. This is required because Docker containers are currently limited to 10
GB of disk usage, and this will quickly get used up if the vm disks are written
inside the container directly. In the command below I'm using
/storage/docker/lib, but any host path with at least 30 GB free should do.

        docker run \
            -it \
            --name instack-virt-setup \
            --privileged \
            --volume /storage/docker/lib:/var/lib/libvirt/images \
            slagle/instack-virt-setup
        


Building the instack-virt-setup Docker image
--------------------------------------------
There is no reason to build the Docker image yourself if you pulled it
following the comamnd above. These steps are here just to document the build
process.

Building the docker image is a multi-step process. There is a Dockerfile to
help with building the initial image. A container must then be started using
that image, modified, and then committed to a new final image.


1. Build a qcow2 disk image for the instack undercloud vm

        UNDERCLOUD_ROOT_PASSWORD=${UNDERCLOUD_ROOT_PASSWORD:-""}
        UNDERCLOUD_PASSWORD_ARG=
        if [ $UNDERCLOUD_ROOT_PASSWORD ]; then
          UNDERCLOUD_PASSWORD_ARG="--root-password password:$UNDERCLOUD_ROOT_PASSWORD"
        fi

        export UNDERCLOUD_VM_NAME=${UNDERCLOUD_VM_NAME:-"instack"}

        virt-builder fedora-20 $UNDERCLOUD_PASSWORD_ARG \
          --size 30G \
          --format qcow2 \
          -o $UNDERCLOUD_VM_NAME.qcow2 \
          --install net-tools,yum-utils,git \
          --firstboot-command \
            'useradd -m -G wheel -p "" stack ; echo "stack:stack" | chpasswd' \
          --firstboot-command \
            'echo "stack ALL=(root) NOPASSWD:ALL" >> /etc/sudoers.d/stack ; chmod 0440 /etc/sudoers.d/stack'

        # Run image through virt-sparsify
        virt-sparsify instack.qcow2 instack.qcow2.new
        mv instack.qcow2.new instack.qcow2

1. Make sure you have the fedora Docker image pulled

        docker pull fedora

1. Build the initial image

        git clone https://github.com/agroup/instack-undercloud
        cd instack-undercloud
        git checkout docker
        cd docker/instack-virt
        docker build -t instack-virt .

1. Start a container based on that image

        docker run -it --name instack-virt --privileged instack-virt

1. ssh as root to the container, then do the following steps:

        mkdir /var/lib/libvirt/base-images

        su - stack

        # The following are the same steps from instack-virt-setup, with the call to
        # virt-builder removed. We should just update that script to make that
        # call optional.
        source /usr/libexec/openstack-tripleo/devtest_variables.sh
        export NODE_ARCH=${NODE_ARCH:-amd64}

        tripleo devtest_testenv.sh instackenv.json

        sudo virsh undefine --remove-all-storage seed


        UNDERCLOUD_ROOT_PASSWORD=${UNDERCLOUD_ROOT_PASSWORD:-""}
        UNDERCLOUD_PASSWORD_ARG=
        if [ $UNDERCLOUD_ROOT_PASSWORD ]; then
          UNDERCLOUD_PASSWORD_ARG="--root-password password:$UNDERCLOUD_ROOT_PASSWORD"
        fi

        export UNDERCLOUD_VM_NAME=${UNDERCLOUD_VM_NAME:-"instack"}

        tripleo configure-vm \
            --name $UNDERCLOUD_VM_NAME \
            --image /var/lib/libvirt/images/$UNDERCLOUD_VM_NAME.qcow2 \
            --seed \
            --libvirt-nic-driver virtio \
            --arch x86_64 \
            --memory 2097152 \
            --cpus 1

1. Still ssh'd as root to the container, vi /start.sh and replace its contents
   with the following:

        #!/bin/bash

        for i in $(seq 0 4); do 
            if [ ! -f /var/lib/libvirt/images/baremetal_$i.qcow2 ]; then
                qemu-img create -f qcow2 /var/lib/libvirt/images/baremetal_$i.qcow2 31G
            fi
        done

        if [ ! -f /var/lib/libvirt/images/instack.qcow2 ]; then
            qemu-img create -f qcow2 -b /var/lib/libvirt/base-images/instack.qcow2 /var/lib/libvirt/images/instack.qcow2
        fi

        /usr/share/openvswitch/scripts/ovs-ctl start --system-id=random
        supervisord -n
           
1. Back on the docker host, copy the created instack.qcow2 into the
   /var/lib/libvirt/base-images directory in the container.

1. Back on the docker host, stop the container

        docker stop instack-virt

1. Commit the container to a new image

        docker commit instack-virt instack-virt-setup
