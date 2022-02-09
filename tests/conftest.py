import pytest
import os
import tempfile
import shutil
import uuid
import synapseclient
from src.synapse_test_helper import SynapseTestHelper
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope='session')
def syn_test_credentials():
    def _get():
        result = [
            os.environ.get('TEST_SYNAPSE_USERNAME'),
            os.environ.get('TEST_SYNAPSE_PASSWORD')
        ]
        if None in result:
            raise Exception('Environment variables not set: TEST_SYNAPSE_USERNAME or TEST_SYNAPSE_PASSWORD')
        return result

    yield _get


@pytest.fixture(scope='session', autouse=True)
def syn_client(syn_test_credentials):
    syn_user, syn_pass = syn_test_credentials()
    synapse_client = synapseclient.Synapse(skip_checks=True, configPath='')
    synapse_client.login(email=syn_user, password=syn_pass, silent=True, rememberMe=False, forced=True)

    assert SynapseTestHelper.configure(synapse_client)

    return synapse_client


@pytest.fixture(autouse=True)
def configure(syn_client):
    assert SynapseTestHelper.configure(syn_client)


@pytest.fixture
def synapse_test_helper(syn_client):
    assert SynapseTestHelper.configure(syn_client)
    with SynapseTestHelper() as sth:
        yield sth


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
