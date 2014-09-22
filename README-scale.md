instack-undercloud scale mode
=============================

instack-undercloud offers 2 deployment modes: poc and scale.

In poc mode, a minimal baremtal flavor is automatically created and used as
the flavor for all the different role types in an overcloud. Nodes with
different hardware characteristics will be used for any role type as long as
they meet the requirements of the minimal baremetal flavor. Poc mode is the
default, and matches the existing virtual environement setups behavior that
currently exists.

In scale mode, no initial flavors are created. Instead, the deployer must
create a flavor per hardware profile they intend to use in their deployment.
They must also assign each of these flavors to overcloud roles via Heat
template parameters.

The following steps can be used to setup an undercloud in scale deployment
mode.

1. On the virt host, make any hardware characteristic changes to the baremetal
VM's created as part of instack-virt-setup. You can make changes to CPU, Disk,
and Memory.

2. In the instack.answers file, before running the installation script, set
DEPLOYMENT_MODE to scale.

        DEPLOYMENT_MODE=scale

3. After the completed installation, create the baremetal flavors to correspond
to the overcloud roles you intend to deploy. These are example commands.

        nova flavor-create control auto 3072 40 2
        nova flavor-create compute auto 1024 40 1
        nova flavor-create blockstorage auto 1024 40 1
        nova flavor-create swiftstorage auto 1024 40 1
        deploy_kernel_id=$(glance image-show bm-deploy-kernel | awk ' / id / {print $4}')
        deploy_ramdisk_id=$(glance image-show bm-deploy-ramdisk | awk ' / id / {print $4}')
        nova flavor-key control set "cpu_arch"="amd64" "baremetal:deploy_kernel_id"="$deploy_kernel_id" "baremetal:deploy_ramdisk_id"="$deploy_ramdisk_id"
        nova flavor-key compute set "cpu_arch"="amd64" "baremetal:deploy_kernel_id"="$deploy_kernel_id" "baremetal:deploy_ramdisk_id"="$deploy_ramdisk_id"
        nova flavor-key blockstorage set "cpu_arch"="amd64" "baremetal:deploy_kernel_id"="$deploy_kernel_id" "baremetal:deploy_ramdisk_id"="$deploy_ramdisk_id"
        nova flavor-key swiftstorage set "cpu_arch"="amd64" "baremetal:deploy_kernel_id"="$deploy_kernel_id" "baremetal:deploy_ramdisk_id"="$deploy_ramdisk_id"

4. Before running instack-deploy-overcloud, edit instackenv.json and update the
node hardware characterists to match what edits you made to the actual VM's.

5. Export the folling environment variables to set Heat Parmeters for the
flavors to use for each Overcloud role. Any of the following parameters not set
will default to "baremetal".

        export OVERCLOUD_CONTROL_FLAVOR=control
        export OVERCLOUD_COMPUTE_FLAVOR=compute
        export OVERCLOUD_BLOCKSTORAGE_FLAVOR=blockstorage
        export OVERCLOUD_SWIFTSTORAGE_FLAVOR=swiftstorage

6. Continue deploying an Overcloud as normal by sourceing deploy-overcloudrc
and running instack-deploy-overcloud.
