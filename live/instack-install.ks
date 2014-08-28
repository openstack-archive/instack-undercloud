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

cat << EOF >> /mnt/sysimage/home/stack/.config/autostart/instack.desktop
[Desktop Entry]
Encoding=UTF-8
Version=0.9.4
Type=Application
Name=instack
Comment=
Exec=/home/stack/instack-undercloud/scripts/instack-apply-config
OnlyShowIn=XFCE;
StartupNotify=false
Terminal=true
Hidden=false
EOF

%end
