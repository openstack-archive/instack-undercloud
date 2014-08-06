Name:		instack-undercloud
Version:	1.0.4
Release:	1%{?dist}
Summary:	Installation tools to install an undercloud via instack

Group:		Development/Languages
License:	ASL 2.0
URL:		https://github.com/agroup/instack-undercloud
Source0:	%{name}-%{version}.tar.gz

BuildArch:	noarch

Requires:	instack
Requires:	openstack-tripleo
Requires:	openstack-tripleo-heat-templates
Requires:	openstack-tripleo-image-elements
Requires:	openstack-tuskar
Requires:	openstack-tuskar-ui
Requires:	redhat-lsb-core
Requires:	policycoreutils-python

Requires:	selinux-policy >= 3.12.1-179


%description
instack-undercloud is a collection of installation tools to install an
undercloud via python-instack. It contains scripts and elements to complete the
installation.


%prep
%setup -q -n %{name}-%{version}


%install
# elements
install -d -m 755 %{buildroot}/%{_datadir}/%{name}
cp -ar elements/* %{buildroot}/%{_datadir}/%{name}
# scripts
install -d -m 755 %{buildroot}/%{_bindir}
cp -ar scripts/* %{buildroot}/%{_bindir}
# json files
cp -ar json-files %{buildroot}/%{_datadir}/instack-undercloud


%files
%doc README.md
%doc LICENSE
%doc instack-baremetal.answers.sample
%doc instack-virt.answers.sample
%doc deploy-virt-overcloudrc
%doc deploy-baremetal-overcloudrc
%{_datadir}/instack-undercloud
%{_bindir}/instack-install-undercloud
%{_bindir}/instack-install-undercloud-packages
%{_bindir}/instack-prepare-for-overcloud
%{_bindir}/instack-deploy-overcloud
%{_bindir}/instack-deploy-overcloud-tuskarcli
%{_bindir}/instack-test-overcloud
%{_bindir}/instack-build-images
%{_bindir}/instack-virt-setup
%{_bindir}/instack-delete-overcloud
%{_bindir}/instack-delete-overcloud-tuskarcli


%changelog
* Wed Aug 06 2014 James Slagle <jslagle@redhat.com> 1.0.4-1
- Bump instack vm memory to 3GB (jslagle@redhat.com)

* Wed Aug 06 2014 James Slagle <jslagle@redhat.com> 1.0.3-1
- Fix spacing in Requires (jslagle@redhat.com)

* Wed Aug 06 2014 James Slagle <jslagle@redhat.com> 1.0.2-1
- Require at least the needed version of selinux-policy (jslagle@redhat.com)

* Tue Aug 05 2014 James Slagle <jslagle@redhat.com> 1.0.1-1
- Remove selinux-package-updates and swift-package-updates elements, as these
  packages have been pushed live. (jslagle@redhat.com)

* Mon Jul 07 2014 James Slagle <jslagle@redhat.com> 1.0.0-1
- Upload the deployrc file to deploy-overcloudrc since that is the file that CI
  always uses. (jslagle@redhat.com)
- Don't install koji builds on the undercloud, these will be handled by the CI
  config.yml (jslagle@redhat.com)

* Tue Jul 01 2014 James Slagle <jslagle@redhat.com> 0.0.16-1
- Add os-refresh-config-reboot to overcloud images as well (jslagle@redhat.com)
- Temporary SELinux changes until new packages are released (rwsu@redhat.com)
- Update comment about virtual power key (jslagle@redhat.com)

* Tue Jul 01 2014 James Slagle <jslagle@redhat.com> 0.0.15-1
- Build images with SELinux enabled (rwsu@redhat.com)
- Switch back to localhost from LOCAL_IP (rwsu@redhat.com)
- Remove selinux-permissive element (rwsu@redhat.com)
- Remove 00-setenforce-0 file to enable SELinux (rwsu@redhat.com)

* Thu Jun 26 2014 James Slagle <jslagle@redhat.com> 0.0.14-1
- Add element to run os-refresh-config on reboot (jslagle@redhat.com)
- Copy the answers and deployrc file into the instack vm (jslagle@redhat.com)
- Fix delete scripts (rbrady@redhat.com)
- Use the devtest_testenv.sh generated id_rsa_virt_power ssh key as the virtual
  power ssh key. (jslagle@redhat.com)
- always do baremetal clean up (charles.crouch@gmail.com)
- Switch to rabbitmq-server from qpidd (rwsu@redhat.com)

* Wed May 28 2014 James Slagle <jslagle@redhat.com> 0.0.13-1
- Create logfile directory before redirecting output via tee
  (jslagle@redhat.com)

* Tue May 27 2014 James Slagle <jslagle@redhat.com> 0.0.12-1
- Package overcloud delete scripts (jslagle@redhat.com)
- Use updated os-apply-config template path (jslagle@redhat.com)
- Update instack-delete-overcloud-tuskarcli (ryan@ryanbrady.org)
- Wait for cloud-final to complete before continuing on the test
  (james.slagle@gmail.com)
- Update README-packages.md (james.slagle@gmail.com)
- Delete existing images in Glance before loading (bnemec@redhat.com)
- added initial draft of scripts for resetting the instack env for additional
  overcloud runs (rbrady@redhat.com)
- Add sample deployrc files (jslagle@redhat.com)
- Use package install type for pip and ironicclient when building overcloud
  images (jslagle@redhat.com)
* Fri Apr 25 2014 James Slagle <jslagle@redhat.com> 0.0.11-1
- Revert "add --selinux-relabel option when creating instack image"
  (jslagle@redhat.com)
- Add stable-interface-names to overcloud image builds (jslagle@redhat.com)

* Wed Apr 23 2014 James Slagle <jslagle@redhat.com> 0.0.10-1
- Updated default arch to amd64 (ryan@ryanbrady.org)
- Use upstream fedora cloud image as fedora-user.qcow2 (jslagle@redhat.com)
- Fix parsing of security group id (rwsu@redhat.com)
- stop using Red Hat theme for undercloud horizon (charles.crouch@gmail.com)
- Changed source of security group info (ryan@ryanbrady.org)
- add --selinux-relabel option when creating instack image (rwsu@redhat.com)
- Added override for overcloud image url source (ryan@ryanbrady.org)

* Wed Apr 16 2014 Ben Nemec <bnemec@redhat.com> 0.0.9-1
- No longer specify --port-range-max for icmp security group rule.
  (jslagle@redhat.com)
- Update README-source.md (james.slagle@gmail.com)
- Update README-packages.md (james.slagle@gmail.com)
- Adds instructions on how to use the rdo staging repository if desired
  (jslagle@redhat.com)
- Use mariadb-rdo element in controller image build (jslagle@redhat.com)
- Make sure yum-utils is always installed (jslagle@redhat.com)

* Tue Apr 15 2014 James Slagle <jslagle@redhat.com> 0.0.8-1
- Fix array references (jslagle@redhat.com)

* Tue Apr 15 2014 James Slagle <jslagle@redhat.com> 0.0.7-1
- Delete initial flavors (jslagle@redhat.com)
- os-*-config packages now pushed to stable (jslagle@redhat.com)
- Make PM vars arrays so they can be indexed (jslagle@redhat.com)
- Load deploy images in instack-prepare-for-overcloud, but delete them before
  running setup-baremetal in the deploy scripts (jslagle@redhat.com)
* Tue Apr 15 2014 James Slagle <jslagle@redhat.com> 0.0.6-1
- Remove rdo-release-icehouse package so the subsequent install doesn't fail
  (jslagle@redhat.com)
- Make enabling the RDO icehouse repo a manual step (jslagle@redhat.com)
- Remove mariadb log workaround (jslagle@redhat.com)
- Remove pip install, no longer needed (jslagle@redhat.com)
- Remove vim-minimal workaround (jslagle@redhat.com)
- fedora-rdo-icehouse was renamed to fedora-rdo-icehouse-repository in latest
  openstack-tripleo-image-elements package (jslagle@redhat.com)
- Update to work with latest openstack-tripleo package (jslagle@redhat.com)
- Use mariadb-rdo element (jslagle@redhat.com)
- root password is no longer hard coded (ryan@ryanbrady.org)
- updated docs to reflect options for instack-virt-setup (rbrady@redhat.com)
- changed root password to default to random but allow to override
  (rbrady@redhat.com)

* Fri Apr 11 2014 James Slagle <jslagle@redhat.com> 0.0.5-1
- Default SWIFTSTORAGESCALE to 1 (jslagle@redhat.com)

* Fri Apr 11 2014 James Slagle <jslagle@redhat.com> 0.0.4-1
- Switch to tito VersionTagger (jslagle@redhat.com)
- added warning against running as root. (rbrady@redhat.com)
- Install test builds of os-*-config (jslagle@redhat.com)

* Fri Apr 11 2014 James Slagle <jslagle@redhat.com> 0.0.3-1
- Install test builds of os-*-config (jslagle@redhat.com)
- Install mariadb-galera-server instead, it is the default in rdo icehouse
  (jslagle@redhat.com)
- added more info to make it clearer where to install undercloud
  (rbrady@redhat.com)

* Thu Apr 10 2014 James Slagle <jslagle@redhat.com> 0.0.2-1
- Use mariadb-galera-server (jslagle@redhat.com)

* Thu Apr 10 2014 James Slagle <jslagle@redhat.com> 0.0.1-1
- Update spec to no longer build from git commits (jslagle@redhat.com)
- Update Building-RPMs.md (james.slagle@gmail.com)

* Wed Apr 09 2014 James Slagle <jslagle@redhat.com> 0-0.10.20140409git
- Update spec file (jslagle@redhat.com)
- Update source install script (jslagle@redhat.com)
- Update instack-virt-setup (james.slagle@gmail.com)
- removed call to instack-install-dependencies as we are now calling the
  upstream version (rbrady@redhat.com)
- updated repo location for image download to publicly accessible
  fedorapeople.org (rbrady@redhat.com)
- Add swiftstorage flavor update for tuskar (jslagle@redhat.com)
- Add explicit installs of openstack-dashboard (jslagle@redhat.com)
- Install needed python-posix_ipc manually (jslagle@redhat.com)
- Newer horizon builds are now available (jslagle@redhat.com)

* Tue Apr 08 2014 James Slagle <jslagle@redhat.com> 0-0.10.20140408git
- Build with tito.
- Update to remove horizon test builds

* Mon Apr 07 2014 James Slagle <jslagle@redhat.com> 0-0.9.20140407git
- Add Requires for tuskar, redhat-lsb-core, and policycoreutils-python
- Bump to latest from git

* Thu Apr 03 2014 James Slagle <jslagle@redhat.com> 0-0.8.20140403git
- Remove code that depends on updates-testing repo

* Wed Apr 02 2014 James Slagle <jslagle@redhat.com> 0-0.7.20140402git
- Bump to latest from git.
- Reset version to 0

* Tue Apr 01 2014 James Slagle <jslagle@redhat.com> 0.0.1-0.7.20140401git
- Bump to latest from git.

* Fri Mar 28 2014 James Slagle <jslagle@redhat.com> 0.0.1-0.6.20140328git
- Install novnc from package

* Thu Mar 27 2014 James Slagle <jslagle@redhat.com> 0.0.1-0.5.20140327git
- Bump to latest from git.
- Add restart for openstack-tuskar-api to instack-deploy-overcloud-tuskarcli
- Add cinder and swift tests to instack-test-overcloud

* Wed Mar 26 2014 James Slagle <jslagle@redhat.com> 0.0.1-0.4.20140326git
- Bump to latest from git.

* Tue Mar 25 2014 James Slagle <jslagle@redhat.com> 0.0.1-0.3.20140325git
- Bump to latest from git.

* Mon Mar 24 2014 James Slagle <jslagle@redhat.com> 0.0.1-0.1.20140324git
- Bump to latest from git.
- Fix Summary and remove empty build.

* Thu Mar 20 2014 James Slagle <jslagle@redhat.com> 0.0.1-0.1.20140319git
- Add new scripts instack-build-images and instack-virt-setup
- Add Requires on other tripleo rpm's.

* Thu Mar 13 2014 James Slagle <jslagle@redhat.com> 0.0.1-0.1.20140314git
- All scripts are now prefixed with instack-*
- Add new instack-deploy-overcloud-tuskarcli script
- Use _datadir macro instead of _datarootdir

* Wed Feb 26 2014 James Slagle <jslagle@redhat.com> 0.0.1-0.1.20140226git
- Add scripts for prepare-for-overcloud and test-overcloud

* Mon Feb 24 2014 James Slagle <jslagle@redhat.com> 0.0.1-0.1.20140224git
- Update install-undercloud-packages to account for new element location

* Mon Feb 24 2014 James Slagle <jslagle@redhat.com> 0.0.1-0.1.20140219git
- Use alphatag macro for the release.
- Update path where elements are installed.

* Tue Feb 18 2014 James Slagle <jslagle@redhat.com> 0.0.1-0.1
- Initial rpm build.
