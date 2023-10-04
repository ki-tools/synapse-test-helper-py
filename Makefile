.PHONY: pip_install
pip_install:
	pipenv install --dev
	pip install --upgrade build


.PHONY: test
test:
	pytest -v --cov --cov-report=term --cov-report=html


.PHONY: build
build: clean docs
	python -m build
	twine check dist/*


.PHONY: clean
clean:
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


.PHONY: publish
publish: build
	python -m twine upload dist/*


.PHONY: uninstall
uninstall:
	pip uninstall -y synapse-test-helper
