FROM fedora
MAINTAINER James Slagle <slagle@redhat.com>

RUN yum -y install supervisor

RUN yum -y install openssh-server
RUN echo root | passwd --stdin root
EXPOSE 22
COPY sshd.ini /etc/supervisord.d/sshd.ini
RUN ssh-keygen -t rsa -f /etc/ssh/ssh_host_rsa_key -N '' 

RUN yum -y install libvirt libvirt-daemon-kvm
COPY libvirtd.ini /etc/supervisord.d/libvirtd.ini

RUN yum -y install openvswitch

COPY start.sh /start.sh
RUN chmod 0755 /start.sh
CMD /start.sh

RUN useradd stack
RUN echo stack | passwd --stdin stack
RUN echo "stack ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/stack
RUN chmod 0440 /etc/sudoers.d/stack

RUN echo 'export LIBVIRT_DEFAULT_URI="qemu:///system"' >> /home/stack/.bashrc

RUN yum install -y http://rdo.fedorapeople.org/openstack-icehouse/rdo-release-icehouse.rpm
RUN yum install -y instack-undercloud
RUN yum install -y libguestfs-tools

RUN groupadd libvirtd
RUN usermod -a -G libvirtd stack
RUN sed -i "s/^#unix_sock_group.*/unix_sock_group = \"libvirtd\"/g" /etc/libvirt/libvirtd.conf; \
    sed -i 's/^#auth_unix_rw.*/auth_unix_rw = "none"/g' /etc/libvirt/libvirtd.conf; \
    sed -i 's/^#unix_sock_rw_perms.*/unix_sock_rw_perms = "0770"/g' /etc/libvirt/libvirtd.conf

RUN yum -y install libvirt-python

RUN yum clean all
