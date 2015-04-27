VERSION := $(shell python setup.py --version)
$(info == Making version $(VERSION))

all:
	python setup.py build

sources:
	$(eval TMPDIR := $(shell mktemp -d))
	tar czf "$(TMPDIR)/smoker.tar.gz" ../smoker
	mv "$(TMPDIR)/smoker.tar.gz" smoker.tar.gz
	rmdir "$(TMPDIR)"
	# Generate spec file - needs to be in repository root to work with Koji
	sed -e s,\%VERSION\%,$(VERSION),g \
		contrib/smoker.spec > smoker.spec

install:
	python setup.py install

rpm: sources
	# Prepare directories and sources for rpmbuild
	mkdir -p build/rpm/SRPMS
	mkdir -p build/rpm/BUILD
	mkdir -p build/rpm/SOURCES
	cp smoker*.tar.gz build/rpm/SOURCES/
	mkdir -p build/rpm/SPECS
	cp smoker.spec build/rpm/SPECS/
	# Build RPM
	rpmbuild --define "_topdir $(CURDIR)/build/rpm" -ba build/rpm/SPECS/smoker.spec

clean:
	python setup.py clean
	rm -f smoker.tar.gz
	rm -rf smoker.egg-info
	rm -rf build
	rm -rf dist
	rm -f smoker.spec

upload:
	# You need following in ~/.pypirc to be able to upload new build
	# Also you need to be a maintainer or owner of gdc-smoker package
	#
	#	[distutils]
	#	index-servers = pypi
	#
	#	[pypi]
	#	repository: https://pypi.python.org/pypi
	#	username: xyz
	#	password: xyz
	#
	@while [ -z "$$CONTINUE" ]; do \
		read -r -p "Are you sure you want to upload version $(VERSION) to Pypi? [y/N] " CONTINUE; \
	done ; \
	if [ "$$CONTINUE" != "y" ]; then \
		echo "Exiting." ; exit 1 ; \
	fi

	python setup.py sdist upload

tag:
	git tag "v$(VERSION)"

release: tag upload
	$(info == Tagged and uploaded new version, do not forget to push new release tag and draft release on Github)
