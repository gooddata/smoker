%bcond_with check

Name:		smoker
Version:	2.3.2
Release:	2%{?dist}
Epoch:		1
Summary:	Smoke Testing Framework

License:	BSD
URL:		https://github.com/gooddata/smoker
Source0:	%{name}.tar.gz

BuildArch:	noarch

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-pip
BuildRequires:  python3-wheel
BuildRequires:  pyproject-rpm-macros
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
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files smoker
install -d %{buildroot}%{_unitdir}
install -pm644 -t %{buildroot}%{_unitdir} smokerd.service

%if %{with check}
%check
%python3 -m pytest -vv
%endif

%files -f %{pyproject_files}
%doc etc/*
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

%changelog
* Sat Jul 04 2026 Robert Moucha <robert.moucha@gooddata.com> - 1:2.3.2-2
- Drop EL7/python2 support. Target EL9+ and Fedora 43+, where python3 is
  always >= 3.9; remove the now-dead %%py2_build/%%py2_install/%%python2
  branches and the python2_sitelib %%files entries.

* Sat Jul 04 2026 Robert Moucha <robert.moucha@gooddata.com> - 1:2.3.2-1
- Migrate the non-EL7 build to %%pyproject_wheel/%%pyproject_install; %%py3_build
  and %%py3_install are deprecated and slated for removal in Fedora 45.
