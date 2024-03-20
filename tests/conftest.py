import pytest
import os
import tempfile
import shutil
import uuid
import synapseclient
from src.synapse_test_helper import SynapseTestHelper
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture()
def syn_test_credentials():
    def _get():
        result = os.environ.get('TEST_SYNAPSE_AUTH_TOKEN', None)
        if result is None:
            raise Exception('Environment variable not set: result TEST_SYNAPSE_AUTH_TOKEN')
        return result

    yield _get


@pytest.fixture()
def mk_syn_client(syn_test_credentials):
    def _m():
        syn_auth_token = syn_test_credentials()
        synapse_client = synapseclient.Synapse(skip_checks=True, configPath='')
        synapse_client.login(authToken=syn_auth_token, silent=True, rememberMe=False, forced=True)
        return synapse_client

    yield _m


@pytest.fixture
def synapse_test_helper(mk_syn_client):
    with SynapseTestHelper(mk_syn_client()) as synapse_test_helper:
        assert synapse_test_helper.configured
        yield synapse_test_helper


@pytest.fixture()
def syn_client(synapse_test_helper, mk_syn_client):
    return synapse_test_helper.client


@pytest.fixture
def temp_file(mk_tempfile):
    """Generates a temp file containing a random string.
    Returns:
        Path to temp file.
    """
    yield mk_tempfile()


@pytest.fixture()
def mk_tempdir():
    created = []

    def _mk():
        path = tempfile.mkdtemp()
        created.append(path)
        return path

    yield _mk

    for path in created:
        if os.path.isdir(path):
            shutil.rmtree(path)


@pytest.fixture()
def mk_tempfile(mk_tempdir):
    temp_file_paths = []

    def _mk(content=str(uuid.uuid4()), dir=None, prefix=None, suffix=None):
        if dir is None:
            dir = mk_tempdir()

        fd, tmp_filename = tempfile.mkstemp(dir=dir, prefix=prefix, suffix=suffix)
        temp_file_paths.append(tmp_filename)
        with os.fdopen(fd, 'w') as tmp:
            tmp.write(content)
        return tmp_filename

    yield _mk

    for path in temp_file_paths:
        if os.path.isfile(path):
            os.remove(path)
