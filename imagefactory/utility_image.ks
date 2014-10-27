url --url=http://download.eng.brq.redhat.com/pub/fedora/releases/20/Fedora/x86_64/os/
# Without the Everything repo, we cannot install cloud-init
repo --name="fedora-everything" --baseurl=http://download.eng.brq.redhat.com/pub/fedora/releases/20/Everything/x86_64/os/
repo --name="updates" --baseurl=http://download.eng.brq.redhat.com/pub/fedora/linux/updates/20/x86_64/
repo --name=openstack --baseurl=http://repos.fedorapeople.org/repos/openstack/openstack-juno/fedora-20/

# Uncomment the following line to use the copr repository
# repo --name=copr-openstack-m --baseurl=http://copr-be.cloud.fedoraproject.org/results/slagle/openstack-m/fedora-$releasever-$basearch/

install
text
keyboard us
lang en_US.UTF-8

skipx

network --device eth0 --bootproto dhcp
rootpw ROOTPW
firewall --disabled
authconfig --enableshadow --enablemd5
selinux --enforcing
timezone --utc America/New_York
bootloader --location=mbr --append="console=tty0 console=ttyS0,115200"
zerombr
clearpart --all --drives=vda

part biosboot --fstype=biosboot --size=1
part /boot --fstype ext4 --size=200 --ondisk=vda
part pv.2 --size=1 --grow --ondisk=vda
volgroup VolGroup00 --pesize=32768 pv.2
logvol swap --fstype swap --name=LogVol01 --vgname=VolGroup00 --size=768 --grow --maxsize=1536
logvol / --fstype ext4 --name=LogVol00 --vgname=VolGroup00 --size=1024 --grow
reboot

%packages
@core
qemu-img
instack-undercloud
git
%end

