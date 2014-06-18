Instack Docker Setup
====================

The instack Docker setup provides an environment equivalent to that produced by
running instack-virt-setup in a reuseable Docker container.


Running the instack-virt-setup Docker image
-------------------------------------------

Pull the image from the docker registry.

        docker pull slagle/instack-virt

Run the image. The container must be started with --privileged so that libvirt
has access to create networks. A host path must also be mounted into the
container at /var/lib/libvirt/images for the instack vm's to use for their
disks. This is required because Docker containers are currently limited to 10
GB of disk usage, and this will quickly get used up if the vm disks are written
inside the container directly. In the command below I'm using
/storage/docker/lib, but any host path with at least 50 GB free should do.

        docker run \
            -it \
            --name instack-virt-setup \
            --privileged \
            --volume /storage/docker/lib:/var/lib/libvirt/images \
            slagle/instack-virt-setup
        

ssh as root to the container. The initial root pw is also root. You can use
docker inspect to get the IP address of the container.

Switch to the stack user and start the instack vm

        su - stack
        virsh start instack

The IP address of the instack vm will be 192.168.122.100.  ssh as the stack
user (initial password is stack) to the vm. It may take a minute or 2 for it to
come up.

        ssh stack@192.168.122.100

Continue with
http://openstack.redhat.com/Deploying_an_RDO_Undercloud_with_Instack. You will
not need to create an answers file or deployrc file.


Building the instack-virt-setup Docker image
--------------------------------------------
There is no reason to build the Docker image yourself if you pulled it
following the commands above. These steps are here just to document the build
process.

Building the docker image is a multi-step process. There is a Dockerfile to
assist with building the initial image. 

1. Run through instack-virt-setup on the build host, according to http://openstack.redhat.com/Deploying_RDO_to_a_Virtual_Machine_Environment_using_RDO_via_Instack#Virtual_Host_Setup

1. After the instack vm is started, ssh to the vm and create the answers file
   and deploy-virt-overcloudrc underneath /home/stack. Be sure to populate
   $MACS in deploy-virt-overcloudrc with the actual values of the baremetal vm
   nodes as created from instack-virt-setup.

1. Poweroff the instack vm.

1. Clone this git repository, switch to the docker branch, and cd to the docker
   build directory.

        git clone https://github.com/agroup/instack-undercloud
        cd instack-undercloud
        git checkout docker
        cd docker/instack-virt

1. Copy needed files from the build host into the build directory.

        cp /var/lib/libvirt/images/instack.qcow2 .
        cp /etc/libvirt/qemu/baremetal_* .
        cp /etc/libvirt/qemu/instack.xml .
        cp /etc/libvirt/qemu/networks/default.xml .
        cp /etc/libvirt/qemu/networks/brbm.xml .
        
1. Update the vm xml definitions to remove the selinux relabel command

        sed -i '/selinux/d' instack.xml baremetal_*.xml
        
1. View instack.xml and get the mac address of the default network interface.

1. Edit default.xml and add the following line in the <dhcp> stanza. Replace
   the value for mac with the mac address you got in the previous step.

        <host mac='52:54:00:e1:f3:7e' name='instack' ip='192.168.122.100'/>

1. Build the docker image

        docker build -t instack-virt .

1. Optionally tag and push the image.
