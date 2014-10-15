# Network information
network  --bootproto=dhcp --onboot=on --activate
# System authorization information
auth --useshadow --enablemd5
# System keyboard
keyboard --xlayouts=us --vckeymap=us
# System language
lang en_US.UTF-8
# System timezone
timezone  US/Eastern

%post --nochroot

rm -f /mnt/sysimage/home/stack/Desktop/liveinst.desktop
rm -f /mnt/sysimage/home/stack/.config/autostart/liveinst.desktop

# Disable NetworkManager as well
# rm -f '/mnt/sysimage/etc/systemd/system/dbus-org.freedesktop.NetworkManager.service'
# rm -f '/mnt/sysimage/etc/systemd/system/dbus-org.freedesktop.nm-dispatcher.service'
# rm -f '/mnt/sysimage/etc/systemd/system/multi-user.target.wants/NetworkManager.service'

# firewalld is installed back by anaconda, so we must totally disable it.
rm -f '/mnt/sysimage/etc/systemd/system/basic.target.wants/firewalld.service'
rm -f '/mnt/sysimage/etc/systemd/system/dbus-org.fedoraproject.FirewallD1.service'


cat << EOF >> /mnt/sysimage/home/stack/.config/autostart/instack.desktop
[Desktop Entry]
Encoding=UTF-8
Version=0.9.4
Type=Application
Name=instack
Comment=
Exec=/usr/bin/instack-apply-config
OnlyShowIn=XFCE;
StartupNotify=false
Terminal=true
Hidden=false
EOF

%end
