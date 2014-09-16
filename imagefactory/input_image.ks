url --url=http://download.eng.brq.redhat.com/pub/fedora/releases/20/Fedora/x86_64/os/
# Without the Everything repo, we cannot install cloud-init
repo --name="fedora-everything" --baseurl=http://download.eng.brq.redhat.com/pub/fedora/releases/20/Everything/x86_64/os/
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
part / --fstype="ext4" --size=3000
reboot

%packages
@core
cloud-init
tar

%end
