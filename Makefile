
# default target does nothing
.DEFAULT_GOAL: default
default: ;

init:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
.PHONY: init

start:
	cd images && ./init.sh
	sleep 5
.PHONY: start

stop:
	docker stop stellar
.PHONY: stop

test:
	python -m pytest -v -rs --cov=kin -s -x --fulltrace test
.PHONY: test

wheel:
	python setup.py bdist_wheel
.PHONY: wheel

pypi:
	twine upload dist/*
.PHONY: pypi

clean:
	rm -f .coverage
	find . -name \*.pyc -delete
.PHONY: clean

api-doc:
	mkdir api-ref/build api-ref/rst
	VERSION=$(shell cat kin/version.py | cut -d "\"" -f 2); \
	sed "s@------@$$VERSION@g" -i api-ref/conf.py
	pipenv run sphinx-apidoc kin/ -o api-ref/rst
	pipenv run sphinx-build -b html api-ref/ api-ref/build

.PHONY: api-doc
