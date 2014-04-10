Name:		instack-undercloud
Version:	0.0.1
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
%{_datadir}/instack-undercloud
%{_bindir}/instack-install-undercloud
%{_bindir}/instack-install-undercloud-packages
%{_bindir}/instack-prepare-for-overcloud
%{_bindir}/instack-deploy-overcloud
%{_bindir}/instack-deploy-overcloud-tuskarcli
%{_bindir}/instack-test-overcloud
%{_bindir}/instack-build-images
%{_bindir}/instack-virt-setup


%changelog
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
