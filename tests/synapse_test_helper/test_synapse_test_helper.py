import os
import pytest
import json
import synapseclient
from synapseclient import Project, Folder, File, Team, Wiki
from src.synapse_test_helper import SynapseTestHelper


@pytest.fixture
def filehandle_interface():
    return {
        'id': '',
        'etag': '',
        'createdBy': '',
        'createdOn': '',
        'modifiedOn': '',
        'concreteType': '',
        'contentType': '',
        'contentMd5': '',
        'fileName': '',
        'storageLocationId': '',
        'contentSize': '',
        'status': '',
    }


def test_context_manager(mk_syn_client, mk_tempfile):
    sth = None
    with SynapseTestHelper(mk_syn_client()) as synapse_test_helper:
        sth = synapse_test_helper
        synapse_test_helper.dispose_of(mk_tempfile())
        assert len(sth.trash) == 1

    assert len(sth.trash) == 0


def test_deconfigure(mk_syn_client):
    syn_client = mk_syn_client()
    with SynapseTestHelper(syn_client) as sth:
        assert sth.client == syn_client
        sth.deconfigure()
        assert sth.configured is False
        assert sth._synapse_client is None
        assert sth.client is None

        with pytest.raises(Exception):
            sth.create_project()


def test_configure(syn_client, mk_syn_client):
    syn_client = mk_syn_client()

    with SynapseTestHelper() as sth:
        assert sth.client is None

    # Instance
    with SynapseTestHelper(syn_client) as sth:
        assert id(sth.client) == id(syn_client)
        assert sth.configured is True
        assert sth.deconfigure()
        assert sth.configured is False
        assert sth.configure(syn_client)
        assert sth.configured
        assert id(sth.client) == id(syn_client)

    # Nested
    with SynapseTestHelper(syn_client) as parent_sth:
        assert id(parent_sth.client) == id(syn_client)

        child_syn_client = mk_syn_client()
        with SynapseTestHelper(child_syn_client) as sth_child:
            assert id(sth_child.client) == id(child_syn_client)
            assert sth_child.client == child_syn_client
        assert id(sth_child.client) == id(child_syn_client)

    # Errors
    with pytest.raises(Exception) as ex:
        with SynapseTestHelper() as sth:
            sth.configure(object())
    assert 'synapse_client must be an instance if synapseclient.Synapse' in str(ex)

    with pytest.raises(Exception) as ex:
        with SynapseTestHelper() as sth:
            sth.configure(synapseclient.Synapse())
    assert 'synapse_client must be logged in.' in str(ex)


def test_is_diposable(synapse_test_helper, mk_tempdir, mk_tempfile, filehandle_interface):
    assert synapse_test_helper.is_diposable(None)
    assert synapse_test_helper.is_diposable(Project())
    assert synapse_test_helper.is_diposable(Folder(parentId='syn0'))
    assert synapse_test_helper.is_diposable(File(parentId='syn0'))
    assert synapse_test_helper.is_diposable(Team(parentId='syn0'))
    assert synapse_test_helper.is_diposable(Wiki(parentId='syn0', owner='123'))
    assert synapse_test_helper.is_diposable(mk_tempdir())
    assert synapse_test_helper.is_diposable(mk_tempfile())
    assert synapse_test_helper.is_diposable(object()) is False
    assert synapse_test_helper.is_diposable('') is False
    assert synapse_test_helper.is_diposable('not_abs_path/test') is False
    assert synapse_test_helper.is_diposable(filehandle_interface)


def test_test_id(synapse_test_helper):
    assert synapse_test_helper.test_id == synapse_test_helper._test_id


def test_uniq_name(synapse_test_helper):
    assert synapse_test_helper.test_id in synapse_test_helper.uniq_name()

    last_name = None
    for i in list(range(3)):
        uniq_name = synapse_test_helper.uniq_name(prefix='aaa-', postfix='-zzz')
        assert uniq_name != last_name
        assert uniq_name.startswith(
            'aaa-{0}'.format(synapse_test_helper.test_id))
        assert uniq_name.endswith('-zzz')
        last_name = uniq_name


def test_fake_synapse_id(synapse_test_helper):
    fake_id = synapse_test_helper.fake_synapse_id

    with pytest.raises(synapseclient.core.exceptions.SynapseHTTPError) as ex:
        synapse_test_helper.client.get(fake_id)

    err_str = str(ex.value)
    assert 'The resource you are attempting to access cannot be found' in err_str or 'does not exist' in err_str


def test_dispose_of(synapse_test_helper, mk_tempfile):
    # Add a single object
    for obj in [mk_tempfile(), mk_tempfile()]:
        synapse_test_helper.dispose_of(obj)
        assert obj in synapse_test_helper.trash

    # Add a list of objects
    obj1 = mk_tempfile()
    obj2 = mk_tempfile()
    synapse_test_helper.dispose_of(obj1, obj2)
    assert obj1 in synapse_test_helper.trash
    assert obj2 in synapse_test_helper.trash

    # Does not add duplicates
    synapse_test_helper.dispose_of(obj1, obj2)
    assert len(synapse_test_helper.trash) == 4

    # Allows None
    synapse_test_helper.dispose_of(None, None)
    assert len(synapse_test_helper.trash) == 5

    # Raises exception for non-disposable objects.
    with pytest.raises(ValueError):
        synapse_test_helper.dispose_of(object())


def test_dispose(temp_file, mk_tempdir, synapse_test_helper):
    # Removes an item not in the trash.
    temp_dir = mk_tempdir()
    synapse_test_helper.dispose_of(mk_tempdir())
    assert len(synapse_test_helper.trash) == 1
    synapse_test_helper.dispose(temp_dir)
    assert len(synapse_test_helper.trash) == 1
    assert os.path.exists(temp_dir) is False
    synapse_test_helper.dispose()
    assert len(synapse_test_helper.trash) == 0

    # Raises exception for non-disposable objects.
    with pytest.raises(ValueError):
        synapse_test_helper.dispose(object())

    project = synapse_test_helper.client.store(Project(name=synapse_test_helper.uniq_name()))

    folder = synapse_test_helper.client.store(
        Folder(name=synapse_test_helper.uniq_name(prefix='Folder '), parent=project))

    file = synapse_test_helper.client.store(File(name=synapse_test_helper.uniq_name(
        prefix='File '), path=temp_file, parent=folder))

    filehandle = file['_file_handle']
    copy_file_handle_request = {"copyRequests": [
        {
            "originalFile": {
                "fileHandleId": filehandle['id'],
                "associateObjectId": file.id,
                "associateObjectType": 'FileEntity'
            }
        }
    ]}
    copy_response = synapse_test_helper.client.restPOST('/filehandles/copy',
                                                        body=json.dumps(copy_file_handle_request),
                                                        endpoint=synapse_test_helper.client.fileHandleEndpoint)
    copy_results = copy_response.get("copyResults")
    filehandle = copy_results[0]['newFileHandle']

    team = synapse_test_helper.client.store(
        Team(name=synapse_test_helper.uniq_name(prefix='Team ')))

    wiki = synapse_test_helper.client.store(
        Wiki(title=synapse_test_helper.uniq_name(prefix='Wiki '), owner=project))

    wikiChild = synapse_test_helper.client.store(Wiki(title=synapse_test_helper.uniq_name(
        prefix='Wiki Child '), owner=project, parentWikiId=wiki.id))

    none = None

    disposable_objects = [project, folder, file, filehandle, team, wiki, wikiChild, temp_file, none]

    # Removes individual items in the trash
    synapse_test_helper.dispose(wiki, team)
    assert wiki not in synapse_test_helper.trash
    assert team not in synapse_test_helper.trash

    for disposable_object in disposable_objects:
        synapse_test_helper.dispose_of(disposable_object)
        assert disposable_object in synapse_test_helper.trash

    synapse_test_helper.dispose()
    assert len(synapse_test_helper.trash) == 0

    for disposable_object in disposable_objects:
        if disposable_object is None:
            assert disposable_object not in synapse_test_helper.trash
        elif isinstance(disposable_object, str):
            assert os.path.exists(disposable_object) is False
        else:
            with pytest.raises(synapseclient.core.exceptions.SynapseHTTPError) as ex:
                if isinstance(disposable_object, Wiki):
                    synapse_test_helper.client.getWiki(disposable_object)
                elif isinstance(disposable_object, Team):
                    synapse_test_helper.client.getTeam(disposable_object.id)
                elif synapse_test_helper._is_filehandle(disposable_object):
                    synapse_test_helper.client.restGET('/fileHandle/{0}'.format(disposable_object['id']),
                                                       endpoint=synapse_test_helper.client.fileHandleEndpoint)
                else:
                    synapse_test_helper.client.get(disposable_object, downloadFile=False)

            err_str = str(ex.value)
            assert "Not Found" in err_str or "cannot be found" in err_str or "is in trash can" in err_str or "does not exist" in err_str

    # TODO: check that projects, folders, and files are not in the trash.


def test_dispose_temp_files(synapse_test_helper, mk_tempdir, mk_tempfile):
    # From _create_temp_file
    temp_file1 = synapse_test_helper.create_temp_file()
    temp_file2 = synapse_test_helper.create_temp_file(name='test_temp_file2')
    assert 'test_temp_file2' in temp_file2

    assert synapse_test_helper._is_path(None) is False

    temp_files = [temp_file1, temp_file2]
    for temp_file in temp_files:
        assert synapse_test_helper._is_path(temp_file)
        assert os.path.dirname(temp_file) in synapse_test_helper.trash
        assert temp_file in synapse_test_helper.trash

    synapse_test_helper.dispose()

    for temp_file in temp_files:
        assert os.path.exists(temp_file) is False

    # From manually created folders and files.
    temp_dir = mk_tempdir()
    temp_paths = [temp_dir,
                  mk_tempdir(),
                  mk_tempfile(),
                  mk_tempdir(),
                  mk_tempfile(),
                  mk_tempfile(dir=temp_dir),
                  mk_tempfile(dir=temp_dir),
                  mk_tempfile(dir=temp_dir)
                  ]
    for temp_path in temp_paths:
        assert synapse_test_helper._is_path(temp_path)
        synapse_test_helper.dispose_of(temp_path)
        assert temp_path in synapse_test_helper.trash

    synapse_test_helper.dispose()

    for temp_path in temp_paths:
        assert os.path.exists(temp_path) is False

    # Does not delete a non-empty folder
    temp_dir = mk_tempdir()
    temp_file = mk_tempfile(dir=temp_dir)
    synapse_test_helper.dispose_of(temp_dir)
    synapse_test_helper.dispose()
    assert os.path.exists(temp_dir)
    assert os.path.exists(temp_file)
    assert len(synapse_test_helper.trash) == 0


def test_dispose_filehandles(synapse_test_helper, filehandle_interface):
    assert synapse_test_helper._is_filehandle(None) is False
    assert synapse_test_helper._is_filehandle(filehandle_interface)
    syn_file = synapse_test_helper.create_file()
    syn_filehandle = syn_file['_file_handle']
    not_syn_filehandle = syn_filehandle.copy()
    not_syn_filehandle.pop('status')

    assert synapse_test_helper._is_filehandle(syn_filehandle)
    assert synapse_test_helper.is_diposable(syn_filehandle)
    synapse_test_helper.dispose_of(syn_filehandle)
    assert syn_filehandle in synapse_test_helper.trash
    synapse_test_helper.dispose()
    assert len(synapse_test_helper.trash) == 0

    assert synapse_test_helper._is_filehandle(not_syn_filehandle) is False
    assert synapse_test_helper.is_diposable(not_syn_filehandle) is False
    with pytest.raises(ValueError, match='Non-disposable type'):
        synapse_test_helper.dispose_of(not_syn_filehandle)
    with pytest.raises(ValueError, match='Non-disposable type'):
        synapse_test_helper.dispose(not_syn_filehandle)


def test_create_project(synapse_test_helper):
    disposed = []

    # Uses the name arg
    name = synapse_test_helper.uniq_name()
    project = synapse_test_helper.create_project(name=name)
    assert project.name == name
    disposed.append(project)

    # Uses the prefix arg
    prefix = '-z-z-z-'
    project = synapse_test_helper.create_project(prefix=prefix)
    assert project.name.startswith(prefix)
    disposed.append(project)

    # Generates a name
    project = synapse_test_helper.create_project()
    assert synapse_test_helper.test_id in project.name
    disposed.append(project)

    for project in disposed:
        assert project in synapse_test_helper.trash
    synapse_test_helper.dispose()
    for project in disposed:
        assert project not in synapse_test_helper.trash


def test_create_folder(synapse_test_helper):
    disposed = []

    # Creates the project for the folder and generates a name.
    syn_folder1 = synapse_test_helper.create_folder()
    assert synapse_test_helper.test_id in syn_folder1.name
    syn_parent = synapse_test_helper.client.get(syn_folder1.parentId)
    assert isinstance(syn_parent, synapseclient.Project)
    disposed.append(syn_folder1)

    # Uses the name arg
    name = synapse_test_helper.uniq_name()
    syn_folder2 = synapse_test_helper.create_folder(parent=syn_parent, name=name)
    assert isinstance(syn_folder1, synapseclient.Folder)
    assert syn_folder2.name == name
    assert syn_folder2 in synapse_test_helper.trash
    disposed.append(syn_folder2)

    # Uses the prefix arg
    prefix = '-z-z-z-'
    syn_folder3 = synapse_test_helper.create_folder(parent=syn_parent, prefix=prefix)
    assert syn_folder3.name.startswith(prefix)
    disposed.append(syn_folder3)

    # Generates a name
    syn_folder4 = synapse_test_helper.create_folder(parent=syn_parent)
    assert synapse_test_helper.test_id in syn_folder4.name
    disposed.append(syn_folder4)

    for folder in disposed:
        assert folder in synapse_test_helper.trash
    synapse_test_helper.dispose()
    for folder in disposed:
        assert folder not in synapse_test_helper.trash


def test_create_file(synapse_test_helper, mk_tempfile):
    disposed = []

    # Creates a project for the file and creates a temp file.
    syn_file = synapse_test_helper.create_file()
    assert isinstance(syn_file, synapseclient.File)
    assert os.path.isfile(syn_file.path)
    syn_parent = synapse_test_helper.client.get(syn_file.parentId)
    assert isinstance(syn_parent, synapseclient.Project)
    disposed.append(syn_file.path)

    # Creates with a parent and creates a temp file.
    syn_file = synapse_test_helper.create_file(parent=syn_parent)
    assert isinstance(syn_file, synapseclient.File)
    assert os.path.isfile(syn_file.path)
    assert syn_file.parentId == syn_parent.id
    disposed.append(syn_file.path)

    # Creates with a parent and file.
    temp_file = mk_tempfile()
    syn_file = synapse_test_helper.create_file(parent=syn_parent, path=temp_file)
    assert isinstance(syn_file, synapseclient.File)
    assert syn_file.path == temp_file
    assert syn_file.parentId == syn_parent.id

    # Creates with a different name.
    temp_file = mk_tempfile()
    name = synapse_test_helper.uniq_name()
    syn_file = synapse_test_helper.create_file(parent=syn_parent, path=temp_file, name=name)
    assert isinstance(syn_file, synapseclient.File)
    assert syn_file.path == temp_file
    assert syn_file.parentId == syn_parent.id
    assert syn_file.name == name

    for path in disposed:
        assert path in synapse_test_helper.trash
    synapse_test_helper.dispose()
    for path in disposed:
        assert path not in synapse_test_helper.trash
        assert os.path.exists(path) is False


def test_create_team(synapse_test_helper):
    # Uses the name arg
    name = synapse_test_helper.uniq_name()
    team = synapse_test_helper.create_team(name=name)
    assert team.name == name
    assert team in synapse_test_helper.trash
    synapse_test_helper.dispose()
    assert team not in synapse_test_helper.trash

    # Uses the prefix arg
    prefix = '-z-z-z-'
    team = synapse_test_helper.create_team(prefix=prefix)
    assert team.name.startswith(prefix)

    # Generates a name
    team = synapse_test_helper.create_team()
    assert synapse_test_helper.test_id in team.name


def test_create_wiki(synapse_test_helper):
    project = synapse_test_helper.create_project()

    # Uses the title arg
    title = synapse_test_helper.uniq_name()
    wiki = synapse_test_helper.create_wiki(title=title, owner=project)
    assert wiki.title == title
    assert wiki in synapse_test_helper.trash

    # Uses the prefix arg
    prefix = '-z-z-z-'
    wiki = synapse_test_helper.create_wiki(prefix=prefix, owner=project)
    assert wiki.title.startswith(prefix)

    # Generates a title
    wiki = synapse_test_helper.create_wiki(owner=project)
    assert synapse_test_helper.test_id in wiki.title

    synapse_test_helper.dispose()
    assert len(synapse_test_helper.trash) == 0


def test_create_temp_dir(synapse_test_helper, mk_tempdir):
    dir = mk_tempdir()

    paths = []

    # Creates a temp dir and adds it to the trash.
    for _ in range(5):
        path = synapse_test_helper.create_temp_dir()
        paths.append(path)
        assert os.path.isdir(path)
        assert path in synapse_test_helper.trash

    synapse_test_helper.dispose()
    for path in paths:
        assert os.path.exists(path) is False
        assert os.path.exists(os.path.dirname(path))
    paths.clear()

    # Uses the dir, prefix, and suffix.
    for _ in range(5):
        path = synapse_test_helper.create_temp_dir(dir=dir, prefix='AA-', suffix='-ZZ')
        paths.append(path)
        assert os.path.isdir(path)
        assert os.path.dirname(path) == dir
        assert os.path.basename(path).startswith('AA-')
        assert os.path.basename(path).endswith('-ZZ')
        assert os.path.join(dir, path) in synapse_test_helper.trash
        assert dir not in synapse_test_helper.trash

    synapse_test_helper.dispose()
    for path in paths:
        assert os.path.exists(path) is False
        assert os.path.exists(dir)
    paths.clear()

    # Uses the name.
    for count in range(5):
        name = 'file_{0}.txt'.format(count)
        path = synapse_test_helper.create_temp_dir(name=name)
        paths.append(path)
        assert os.path.isdir(path)
        assert os.path.basename(path) == name
        assert path in synapse_test_helper.trash
        assert os.path.dirname(path) in synapse_test_helper.trash

    synapse_test_helper.dispose()
    for path in paths:
        assert os.path.exists(path) is False
        assert os.path.exists(os.path.dirname(path)) is False
    paths.clear()

    # Uses the name, dir, prefix, and suffix.
    for count in range(5):
        name = 'folder_{0}'.format(count)
        path = synapse_test_helper.create_temp_dir(name=name, dir=dir, prefix='AA-', suffix='-ZZ')
        paths.append(path)
        assert os.path.isdir(path)
        assert os.path.dirname(path) == dir
        assert os.path.basename(path) == 'AA-{0}-ZZ'.format(name)
        assert os.path.join(dir, path) in synapse_test_helper.trash
        assert dir not in synapse_test_helper.trash

    synapse_test_helper.dispose()
    for path in paths:
        assert os.path.exists(path) is False
        assert os.path.exists(os.path.dirname(path))
    paths.clear()

    # Creates any missing parent directories
    new_path = os.path.join(dir, 'one', 'two')
    assert os.path.exists(new_path) is False
    path = synapse_test_helper.create_temp_dir(dir=new_path)
    assert os.path.isdir(os.path.dirname(path))

    new_path = os.path.join(dir, 'three', 'four')
    assert os.path.exists(new_path) is False
    path = synapse_test_helper.create_temp_dir(name='folder', dir=new_path)
    assert os.path.isdir(os.path.dirname(path))


def test_create_temp_file(synapse_test_helper, mk_tempdir):
    dir = mk_tempdir()

    paths = []

    # Creates a temp dir and file and adds each to the trash.
    for _ in range(5):
        path = synapse_test_helper.create_temp_file()
        paths.append(path)
        assert os.path.isfile(path)
        assert path in synapse_test_helper.trash
        assert os.path.dirname(path) in synapse_test_helper.trash

    synapse_test_helper.dispose()
    for path in paths:
        assert os.path.exists(path) is False
        assert os.path.exists(os.path.dirname(path)) is False
    paths.clear()

    # Uses the dir, prefix, and suffix.
    for _ in range(5):
        path = synapse_test_helper.create_temp_file(dir=dir, prefix='AA-', suffix='-ZZ')
        paths.append(path)
        assert os.path.isfile(path)
        assert os.path.dirname(path) == dir
        assert os.path.basename(path).startswith('AA-')
        assert os.path.basename(path).endswith('-ZZ')
        assert os.path.join(dir, path) in synapse_test_helper.trash
        assert dir not in synapse_test_helper.trash

    synapse_test_helper.dispose()
    for path in paths:
        assert os.path.exists(path) is False
        assert os.path.exists(dir)
    paths.clear()

    # Uses the name.
    for count in range(5):
        name = 'file_{0}.txt'.format(count)
        path = synapse_test_helper.create_temp_file(name=name)
        paths.append(path)
        assert os.path.isfile(path)
        assert os.path.basename(path) == name
        assert path in synapse_test_helper.trash
        assert os.path.dirname(path) in synapse_test_helper.trash

    synapse_test_helper.dispose()
    for path in paths:
        assert os.path.exists(path) is False
        assert os.path.exists(os.path.dirname(path)) is False
    paths.clear()

    # Uses the name, dir, prefix, and suffix.
    for count in range(5):
        name = 'file_{0}.txt'.format(count)
        path = synapse_test_helper.create_temp_file(name=name, dir=dir, prefix='AA-', suffix='-ZZ')
        paths.append(path)
        assert os.path.isfile(path)
        assert os.path.dirname(path) == dir
        assert os.path.basename(path) == 'AA-{0}-ZZ'.format(name)
        assert os.path.join(dir, path) in synapse_test_helper.trash
        assert dir not in synapse_test_helper.trash

    synapse_test_helper.dispose()
    for path in paths:
        assert os.path.exists(path) is False
        assert os.path.exists(os.path.dirname(path))
    paths.clear()

    # Writes content to the file.
    contents = 'some file text...'
    path = synapse_test_helper.create_temp_file(content=contents)
    with open(path) as f:
        assert f.read() == contents

    # Creates any missing parent directories
    new_path = os.path.join(dir, 'one', 'two')
    assert os.path.exists(new_path) is False
    path = synapse_test_helper.create_temp_file(dir=new_path)
    assert os.path.isdir(os.path.dirname(path))

    new_path = os.path.join(dir, 'three', 'four')
    assert os.path.exists(new_path) is False
    path = synapse_test_helper.create_temp_file(name='test.txt', dir=new_path)
    assert os.path.isdir(os.path.dirname(path))
