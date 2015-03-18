# Minimal Disk Image
#
# Firewall configuration
firewall --enabled
# Use network installation
url --url="http://mirror.pnl.gov/fedora/linux/releases/20/Everything/x86_64/os/"
repo --name=updates --baseurl="http://mirror.pnl.gov/fedora/linux/updates/20/x86_64/" 


# Root password
rootpw --plaintext removethispw
# Network information
network  --bootproto=dhcp --onboot=on --activate
# System authorization information
auth --useshadow --enablemd5
# System keyboard
keyboard --xlayouts=us --vckeymap=us
# System language
lang en_US.UTF-8
# SELinux configuration
selinux --enforcing
# Installation logging level
logging --level=info
# Shutdown after installation
shutdown
# System timezone
timezone  US/Eastern
# System bootloader configuration
bootloader --location=mbr
# Clear the Master Boot Record
zerombr
# Partition clearing information
clearpart --all
# Disk partitioning information
part / --fstype="ext4" --size=4000
part swap --size=1000

xconfig --startxonboot

%post

# Update everything
yum clean all
yum -y update

useradd stack
usermod -G wheel -a stack
echo stack | passwd stack --stdin

# Remove root password
passwd -d root > /dev/null

# fstab from the install won't match anything. remove it and let dracut
# handle mounting.
cat /dev/null > /etc/fstab

# This is a huge file and things work ok without it
rm -f /usr/share/icons/HighContrast/icon-theme.cache

# create /etc/sysconfig/desktop (needed for installation)

cat > /etc/sysconfig/desktop <<EOF
PREFERRED=/usr/bin/startxfce4
DISPLAYMANAGER=/usr/sbin/lightdm
EOF

# deactivate xfconf-migration (#683161)
rm -f /etc/xdg/autostart/xfconf-migration-4.6.desktop || :

# set up lightdm autologin
sed -i 's/^#autologin-user=.*/autologin-user=stack/' /etc/lightdm/lightdm.conf
sed -i 's/^#autologin-user-timeout=.*/autologin-user-timeout=0/' /etc/lightdm/lightdm.conf
#sed -i 's/^#show-language-selector=.*/show-language-selector=true/' /etc/lightdm/lightdm-gtk-greeter.conf

# set Xfce as default session, otherwise login will fail
sed -i 's/^#user-session=.*/user-session=xfce/' /etc/lightdm/lightdm.conf

# Show harddisk install on the desktop
mkdir /home/stack/Desktop
cp /usr/share/applications/liveinst.desktop /home/stack/Desktop
sed -i -e 's/NoDisplay=true/NoDisplay=false/' /home/stack/Desktop/liveinst.desktop
sed -i -e 's/Exec=\/usr\/bin\/liveinst/\0 --kickstart \/usr\/share\/instack-undercloud\/live\/instack-install.ks/' /home/stack/Desktop/liveinst.desktop
sed -i -e 's/Terminal=false/Terminal=true/' /home/stack/Desktop/liveinst.desktop
mkdir -p  /home/stack/.config/autostart
ln -s /home/stack/Desktop/liveinst.desktop /home/stack/.config/autostart

# and mark it as executable (new Xfce security feature)
chmod +x /home/stack/Desktop/liveinst.desktop

# deactivate xfce4-panel first-run dialog (#693569)
mkdir -p /home/stack/.config/xfce4/xfconf/xfce-perchannel-xml
cp /etc/xdg/xfce4/panel/default.xml /home/stack/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml

pushd /home/stack

ssh-keygen -t rsa -N "" -f /home/stack/virtual-power-key

curl -o /etc/yum.repos.d/slagle-openstack-m.repo https://copr.fedoraproject.org/coprs/slagle/openstack-m/repo/fedora-20/slagle-openstack-m-fedora-20.repo
yum -y install https://slagle.fedorapeople.org/copr/instack-undercloud-1.0.10-1.fc20.noarch.rpm
cp /usr/share/doc/instack-undercloud/instack.answers.sample /home/stack/instack.answers
# instack-install-undercloud sources ~/instack.answers, and during the
# %chroot phase, apparently ~ evaluates to /tmp. So, we need to copy the
# answers file there as well.
cp /usr/share/doc/instack-undercloud/instack.answers.sample ~/instack.answers

export RUN_ORC=0
instack-install-undercloud-source

cat << EOF >> /etc/fstab
tmpfs /mnt tmpfs rw 0 0
EOF

# Clean up answers file
rm -f ~/instack.answers

popd

# this goes at the end after all other changes. 
chown -R stack:stack /home/stack
restorecon -R /home/stack

# disable os-collect-config
rm -f /etc/systemd/system/multi-user.target.wants/os-collect-config.service
# disable crond so that os-refresh-config on boot job does not start
rm -f /etc/systemd/system/multi-user.target.wants/crond.service

# need to reinstall anaconda
yum -y install anaconda
# firewalld is installed back by anaconda, so we must totally disable it.
rm '/etc/systemd/system/basic.target.wants/firewalld.service'
rm '/etc/systemd/system/dbus-org.fedoraproject.FirewallD1.service'

%end

%packages
@core
kernel
memtest86+
grub2-efi
grub2
shim
syslinux

anaconda
git
firefox
ucs-miscfixed-fonts
bitmap-fixed-fonts
#@virtualization

@xfce-desktop
# @xfce-apps
# @xfce-extra-plugins
# @xfce-media
# @xfce-office

@base-x
# @guest-desktop-agents
# @standard
@input-methods
@hardware-support


# unlock default keyring. FIXME: Should probably be done in comps
gnome-keyring-pam

-dracut-config-rescue

-dnf

# Try to get around the broken dep during the instack install around
# glibc-devel, adding packages manually here.
libffi-devel
gcc
python-devel
openssl-devel
libxml2-devel
libxslt-devel

%end
