%global with_check 0

Name:		smoker
Version:	2.1.7
Release:	1%{?dist}
Epoch:		1
Summary:	Smoke Testing Framework

Group:		Applications/System
License:	BSD
URL:		https://github.com/gooddata/smoker
Source0:	smoker.tar.gz

BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:	noarch
BuildRequires:	python2-devel python-setuptools-devel python-flask-restful python-setproctitle python-psutil python-simplejson python-argparse PyYAML
Requires:	python-flask-restful >= 1:0.3.1-5
Requires:	python-setproctitle
Obsoletes:	gdc-smoker

%if 0%{?el6}
Requires(post): chkconfig
Requires(preun): chkconfig
Requires(preun): initscripts
%else
BuildRequires:  systemd
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd
%endif


%description
Smoker (aka Smoke Testing Framework) is a framework for distributed execution
of Python modules, shell commands or external tools. It executes configured
plugins on request or periodically, unifies output and provide it via REST API
for it's command-line or other client.

%prep
%setup -q -c

%build
%{__python} setup.py build

%install
%{__rm} -rf %{buildroot}
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
mkdir -p %{buildroot}/usr/share/doc/smoker/
install -m 644 etc/* %{buildroot}/usr/share/doc/smoker/
%if 0%{?el6}
install -m 755 -D rc.d/init.d/smokerd %{buildroot}/etc/rc.d/init.d/smokerd
%else
install -d %{buildroot}/%{_unitdir}
install -pm644 smokerd.service %{buildroot}/%{_unitdir}/smokerd.service
%endif

%if 0%{?with_check}
%check
%{__python} setup.py test
%endif #with_check

%clean
%{__rm} -rf %{buildroot}

%files
%defattr(-,root,root,-)
%{python_sitelib}/*.egg-info
%{python_sitelib}/smoker
%if 0%{?el6}
/etc/rc.d/init.d/smokerd
%else
%{_unitdir}/smokerd.service
%endif
/usr/share/doc/smoker/smokercli-example.yaml
/usr/share/doc/smoker/smokerd-example.yaml
/usr/bin/check_smoker_plugin.py
/usr/bin/smokercli.py
/usr/bin/smokerd.py

%post
%if 0%{?el6}
/sbin/chkconfig --add smokerd
%else
%systemd_post smokerd.service
%endif

%preun
%if 0%{?el6}
[ $1 = 0 ] || exit 0
service smokerd stop 2>&1 >/dev/null
/sbin/chkconfig --del smokerd
%else
%systemd_preun smokerd.service
%endif

%postun
%if 0%{?el6}
  # no action. Restart should be managed by Puppet or manually
  # to prevent service disruption.
  exit 0
%else
  # Just reload daemon, don't restart services
  %systemd_postun
%endif
