%bcond_with check

Name:		smoker
Version:	2.3.2
Release:	0%{?dist}
Epoch:		1
Summary:	Smoke Testing Framework

License:	BSD
URL:		https://github.com/gooddata/smoker
Source0:	%{name}.tar.gz

BuildArch:	noarch

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
%if %{with check}
BuildRequires:  python3dist(pytest)
BuildRequires:  python3dist(mock)
BuildRequires:  python3dist(flask-restful)
BuildRequires:  python3dist(psutil)
BuildRequires:  python3dist(pyyaml)
BuildRequires:  python3dist(setproctitle)
%endif

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
%if 0%{?el7}
%py2_build
%else
%py3_build
%endif

%install
%if 0%{?el7}
%py2_install
%else
%py3_install
%endif
install -d %{buildroot}%{_unitdir}
install -pm644 -t %{buildroot}%{_unitdir} smokerd.service

%if %{with check}
%check
%if 0%{?el7}
%python2 -m pytest -vv
%else
%python3 -m pytest -vv
%endif
%endif

%files
%doc etc/*
%if 0%{?el7}
%{python2_sitelib}/smoker-*.egg-info/
%{python2_sitelib}/smoker/
%else
%{python3_sitelib}/smoker-*.egg-info/
%{python3_sitelib}/smoker/
%endif
%{_unitdir}/smokerd.service
%{_bindir}/check_smoker_plugin.py
%{_bindir}/smokercli.py
%{_bindir}/smokerd.py

%post
%systemd_post smokerd.service

%preun
%systemd_preun smokerd.service

%postun
# Just reload daemon, don't restart services
%systemd_postun smokerd.service
