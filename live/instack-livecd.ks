%include /usr/share/spin-kickstarts/fedora-livecd-xfce.ks

# Network information
network  --device=eth0 --nameserver=8.8.8.8 --bootproto=dhcp --onboot=on --activate

# Disk partitioning information
part / --fstype="ext4" --size=4000
part swap --size=1000

%post

/usr/sbin/useradd stack
/usr/sbin/usermod -G wheel -a stack
echo stack | passwd stack --stdin

# Remove root password
passwd -d root > /dev/null

# Show harddisk install on the desktop
mkdir /home/stack/Desktop
cp /usr/share/applications/liveinst.desktop /home/stack/Desktop
sed -i -e 's/NoDisplay=true/NoDisplay=false/' /home/stack/Desktop/liveinst.desktop
sed -i -e 's/Exec=\/usr\/bin\/liveinst/\0 --kickstart \/home\/stack\/instack-undercloud\/live\/instack-install.ks/' /home/stack/Desktop/liveinst.desktop
sed -i -e 's/Terminal=false/Terminal=true/' /home/stack/Desktop/liveinst.desktop
mkdir -p  /home/stack/.config/autostart
ln -s /home/stack/Desktop/liveinst.desktop /home/stack/.config/autostart

# and mark it as executable (new Xfce security feature)
chmod +x /home/stack/Desktop/liveinst.desktop

# deactivate xfce4-panel first-run dialog (#693569)
mkdir -p /home/stack/.config/xfce4/xfconf/xfce-perchannel-xml
cp /etc/xdg/xfce4/panel/default.xml /home/stack/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml

pushd /home/stack

ssh-keygen -t rsa -N "" -f /home/stack/id_rsa_virt_power

curl -o /etc/yum.repos.d/slagle-openstack-m.repo https://copr.fedoraproject.org/coprs/slagle/openstack-m/repo/fedora-20/slagle-openstack-m-fedora-20.repo
yum -y install instack-undercloud
cp /usr/share/instack-undercloud/instack.answers.sample /home/stack/instack.answers
# instack-install-undercloud sources ~/instack.answers, and during the
# %chroot phase, apparently ~ evaluates to /tmp. So, we need to copy the
# answers file there as well.
cp instack-undercloud/instack-baremetal.answers.sample ~/instack.answers

export RUN_ORC=0
export HOME=/home/stack
export PATH=/usr/bin:/usr/sbin/:/sbin
instack-install-undercloud

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

# need to reinstall anaconda
yum -y install anaconda
# firewalld is installed back by anaconda, so we must totally disable it.
rm '/etc/systemd/system/basic.target.wants/firewalld.service'
rm '/etc/systemd/system/dbus-org.fedoraproject.FirewallD1.service'

# need to reinstall grub2
yum -y install grub2

%end

%packages
anaconda
firefox
ucs-miscfixed-fonts
bitmap-fixed-fonts
shadow-utils

-@xfce-apps
-@xfce-extra-plugins
-@xfce-media
-@xfce-office
-@virtualization

%end
