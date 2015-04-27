sources:
	tar czf /tmp/smoker.tar.gz ../smoker
	mv /tmp/smoker.tar.gz smoker.tar.gz

install:
	python setup.py install

rpm: sources
	mkdir -p ~/rpmbuild/{SPECS,SOURCES}
	cp smoker.spec ~/rpmbuild/SPECS
	cp smoker*.tar.gz ~/rpmbuild/SOURCES
	rpmbuild -ba  ~/rpmbuild/SPECS/smoker.spec

clean:
	python setup.py clean

