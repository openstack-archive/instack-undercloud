%post --chroot

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
