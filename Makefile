.PHONY: pip_install
pip_install:
	pipenv install --dev


.PHONY: test
test:
	pytest -v --cov --cov-report=term --cov-report=html


.PHONY: build
build: clean docs
	python setup.py sdist
	python setup.py bdist_wheel
	twine check dist/*


.PHONY: clean
clean:
	rm -rf ./build/*
	rm -rf ./dist/*
	rm -rf ./htmlcov


.PHONY: docs
docs:
	rm -rf ./docs/*
	pdoc --html --output-dir ./docs ./src/synapse_test_helper
	mv ./docs/synapse_test_helper/* ./docs/
	rmdir ./docs/synapse_test_helper


.PHONY: install_local
install_local:
	pip install -e .


.PHONY: install_test
install_test:
	pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple synapse-test-helper


.PHONY: publish_test
publish_test: build
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*


.PHONY: publish
publish: build
	twine upload dist/*


.PHONY: uninstall
uninstall:
	pip uninstall -y synapse-test-helper
