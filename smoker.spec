%global with_check 0

%if 0%{?el8}
%global _py %{__python3}
%global py_sitelib %{python3_sitelib}
%else
%global _py %{__python2}
%global py_sitelib %{python2_sitelib}
%endif

Name:		smoker
Version:	2.2.0
Release:	1%{?dist}
Epoch:		1
Summary:	Smoke Testing Framework

Group:		Applications/System
License:	BSD
URL:		https://github.com/gooddata/smoker
Source0:	%{name}.tar.gz

BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:	noarch

%if 0%{?el8}
BuildRequires:  python3-setuptools python3-setproctitle python3-psutil
%else
BuildRequires:	python2-devel python2-setuptools python-setproctitle python2-psutil
%endif
Obsoletes:	gdc-smoker

BuildRequires:  systemd
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd


%description
Smoker (aka Smoke Testing Framework) is a framework for distributed execution
of Python modules, shell commands or external tools. It executes configured
plugins on request or periodically, unifies output and provide it via REST API
for it's command-line or other client.

%prep
%setup -q -c

%build
%{_py} setup.py build

%install
%{__rm} -rf %{buildroot}
%{_py} setup.py install -O1 --skip-build --root %{buildroot}
mkdir -p %{buildroot}/usr/share/doc/smoker/
install -m 644 etc/* %{buildroot}/usr/share/doc/smoker/
install -d %{buildroot}/%{_unitdir}
install -pm644 smokerd.service %{buildroot}/%{_unitdir}/smokerd.service

%if 0%{?with_check}
%check

%{_py} setup.py test
%endif #with_check

%clean
%{__rm} -rf %{buildroot}

%files
%defattr(-,root,root,-)
%{py_sitelib}/*.egg-info
%{py_sitelib}/smoker
%{_unitdir}/smokerd.service
/usr/share/doc/smoker/smokercli-example.yaml
/usr/share/doc/smoker/smokerd-example.yaml
/usr/bin/check_smoker_plugin.py
/usr/bin/smokercli.py
/usr/bin/smokerd.py

%post
%systemd_post smokerd.service

%preun
%systemd_preun smokerd.service

%postun
  # Just reload daemon, don't restart services
  %systemd_postun
