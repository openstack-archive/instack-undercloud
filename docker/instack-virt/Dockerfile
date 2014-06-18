FROM fedora
MAINTAINER James Slagle <slagle@redhat.com>

RUN yum -y install supervisor

RUN yum -y install openssh-server
RUN echo root | passwd --stdin root
EXPOSE 22
RUN ssh-keygen -t rsa -f /etc/ssh/ssh_host_rsa_key -N '' 

RUN yum -y install libvirt libvirt-daemon-kvm
COPY libvirtd.ini /etc/supervisord.d/libvirtd.ini

RUN yum -y install openvswitch


RUN useradd stack
RUN echo stack | passwd --stdin stack
RUN echo "stack ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/stack
RUN chmod 0440 /etc/sudoers.d/stack

RUN echo 'export LIBVIRT_DEFAULT_URI="qemu:///system"' >> /home/stack/.bashrc

RUN groupadd libvirtd; usermod -a -G libvirtd stack
RUN sed -i "s/^#unix_sock_group.*/unix_sock_group = \"libvirtd\"/g" /etc/libvirt/libvirtd.conf; \
    sed -i 's/^#auth_unix_rw.*/auth_unix_rw = "none"/g' /etc/libvirt/libvirtd.conf; \
    sed -i 's/^#unix_sock_rw_perms.*/unix_sock_rw_perms = "0770"/g' /etc/libvirt/libvirtd.conf

RUN yum clean all

COPY sshd.ini /etc/supervisord.d/sshd.ini
COPY baremetal_0.xml /etc/libvirt/qemu/baremetal_0.xml
COPY baremetal_1.xml /etc/libvirt/qemu/baremetal_1.xml
COPY baremetal_2.xml /etc/libvirt/qemu/baremetal_2.xml
COPY baremetal_3.xml /etc/libvirt/qemu/baremetal_3.xml
COPY instack.xml /etc/libvirt/qemu/instack.xml
COPY default.xml /etc/libvirt/qemu/networks/default.xml
COPY brbm.xml /etc/libvirt/qemu/networks/brbm.xml
COPY instack.qcow2 /var/lib/libvirt/base-images/instack.qcow2

COPY start.sh /start.sh
RUN chmod 0755 /start.sh
CMD /start.sh
