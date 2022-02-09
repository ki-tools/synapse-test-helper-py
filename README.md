[![Build Status](https://travis-ci.org/ki-tools/synapse-test-helper-py.svg?branch=master)](https://travis-ci.org/ki-tools/synapse-test-helper-py)
[![Coverage Status](https://coveralls.io/repos/github/ki-tools/synapse-test-helper-py/badge.svg?branch=master)](https://coveralls.io/github/ki-tools/synapse-test-helper-py?branch=master)

# synapse-test-helper

Utilities for integration testing against [Synapse](https://www.synapse.org).

## Installation

`pip install synapse-test-helper`

## Usage

Create a fixture that yields a configured instance of SynapseTestHelper using the context manager.

Example:

conftest.py:

```python
from synapse_test_helper import SynapseTestHelper


@pytest.fixture(scope='session', autouse=True)
def syn_client():
    synapse_client = synapseclient.Synapse()
    synapse_client.login()  # Set to use your preferred login method for Synapse.
    SynapseTestHelper.configure(synapse_client)
    return synapse_client


@pytest.fixture
def synapse_test_helper():
    with SynapseTestHelper() as sth:
        yield sth
```

test_my_stuff.py:

```python
def test_my_fuction(synapse_test_helper):
    project = synapse_test_helper.create_project()
    # other test code...
    # when this method ends the project will be deleted on Synapse.
```

## Development Setup

```bash
git clone https://github.com/ki-tools/synapse-test-helper-py.git
cd synapse-test-helper-py
pipenv --three
pipenv shell
make pip_install
```

Run tests:

1. Rename `.env.template` to `.env` and set the variables in the file.
2. Run `make test` or `tox`
