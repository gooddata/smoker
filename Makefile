VERSION := $(shell python setup.py --version)
$(info == Making version $(VERSION))

all:
	python setup.py build

sources:
	$(eval TMPDIR := $(shell mktemp -d))
	tar czf "$(TMPDIR)/smoker.tar.gz" ../smoker
	mv "$(TMPDIR)/smoker.tar.gz" smoker.tar.gz
	rmdir "$(TMPDIR)"

install:
	python setup.py install

rpm: sources
	mkdir -p contrib/rpm/SOURCES
	ln -s smoker*.tar.gz contrib/rpm/SOURCES/
	rpmbuild --define "_topdir $(CURDIR)/contrib/rpm" -ba contrib/rpm/SPECS/smoker.spec

clean:
	python setup.py clean
	rm -f smoker.tar.gz
	rm -rf smoker.egg-info
	rm -rf contrib/rpm/SOURCES
	rm -rf contrib/rpm/BUILD
	rm -rf contrib/rpm/RPMS
	rm -rf contrib/rpm/SRPMS

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
