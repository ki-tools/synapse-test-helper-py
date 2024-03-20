from __future__ import annotations
import typing as t
import logging
import os
import uuid
import time
import tempfile
from pathlib import PurePath
import synapseclient
from synapseclient import Project, Folder, File, Team, Wiki


class SynapseTestHelper:
    """Test helper for working with Synapse."""

    def __init__(self, synapse_client: synapseclient.Synapse = None):
        self._test_id = self._uniq_str()
        self.trash = []
        self._synapse_client = None
        if synapse_client:
            self.configure(synapse_client)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.dispose()

    def configure(
            self,
            synapse_client: synapseclient.Synapse
    ) -> bool:
        self.deconfigure()

        if not isinstance(synapse_client, synapseclient.Synapse):
            raise Exception('synapse_client must be an instance if synapseclient.Synapse.')

        if synapse_client.credentials is None:
            raise Exception('synapse_client must be logged in.')

        self._synapse_client = synapse_client

        return self.configured

    def deconfigure(self) -> bool:
        """Removes configuration."""
        self._synapse_client = None
        return not self.configured

    @property
    def configured(self) -> bool:
        """Gets if configured."""
        return self._synapse_client is not None

    @property
    def client(self) -> synapseclient:
        """Gets the synapseclient."""
        return self._synapse_client

    def _uniq_str(self) -> str:
        """Generates a unique Synapse friendly string."""
        return str(uuid.uuid4()).replace('-', '_')

    @property
    def test_id(self) -> str:
        """Gets a unique value to use as a test identifier.

        This string can be used to help identify the test instance that created the object.
        """
        return self._test_id

    def uniq_name(
            self,
            prefix: str = None,
            postfix: str = None
    ) -> str:
        """Get a unique string that is Synapse friendly with the test_id in it.

        Args:
            prefix: Optional prefix.
            postfix: Optional postfix.

        Returns:
            String
        """
        if prefix is None:
            prefix = self._uniq_str()
        if postfix is None:
            postfix = self._uniq_str()
        return "{0}{1}_{2}{3}".format(prefix, self.test_id, uuid.uuid4().hex, postfix)

    @property
    def fake_synapse_id(self) -> str:
        """Gets a Synapse entity ID that does not exist in Synapse.

        Returns:
            String
        """
        return 'syn0'

    DISPOSABLE_TYPES = [
        synapseclient.Project,
        synapseclient.Folder,
        synapseclient.File,
        synapseclient.Team,
        synapseclient.Wiki
    ]

    DISPOSABLE_SYNAPSE_TYPES = DISPOSABLE_TYPES

    SKIP_SYNAPSE_TRASH_TYPES = [
        synapseclient.Project,
        synapseclient.Folder,
        synapseclient.File,
    ]

    def is_diposable(
            self,
            obj
    ) -> bool:
        """Gets if an object is disposable by SynapseTestHelper."""
        return obj is None or (type(obj) in self.DISPOSABLE_TYPES or self._is_path(obj) or self._is_filehandle(obj))

    def _verify_is_disposable(
            self,
            obj
    ) -> None:
        """Checks that an object can be disposed else raises an exception."""
        if not self.is_diposable(obj):
            raise ValueError('Non-disposable type: {0}'.format(type(obj)))

    def dispose_of(
            self,
            *disposable_objects: list[t.Any]
    ) -> None:
        """Adds a disposable object to the list of objects to be deleted."""
        for obj in disposable_objects:
            self._verify_is_disposable(obj)
            if obj not in self.trash:
                self.trash.append(obj)

    def dispose(
            self,
            *disposable_objects: list[t.Any] | [] | None
    ) -> bool:
        """Deletes any disposable objects that were created during testing.
        This method needs to be manually called after each or all tests are done, or use the context manager.

        Args:
            *disposable_objects: Objects to delete. Can be in the trash or not.

        Returns:
            True if all items were deleted, else False.
        """
        projects = []
        paths = []
        others = []

        objects_to_dispose = disposable_objects if disposable_objects else self.trash

        for obj in objects_to_dispose:
            self._verify_is_disposable(obj)
            if isinstance(obj, Project):
                projects.append(obj)
            elif self._is_path(obj):
                paths.append(obj)
            else:
                others.append(obj)

        # Sort the temp files and folders so each file is removed first then the empty directory.
        # If the directory is not empty then this process should not be the one to delete it. This is for safety!
        paths.sort(reverse=True)

        # Projects need to be deleted first.
        for obj in projects + others + paths:
            try:
                if obj is None:
                    pass
                elif type(obj) in self.SKIP_SYNAPSE_TRASH_TYPES:
                    self.client.restDELETE(uri='/entity/{0}?skipTrashCan=true'.format(obj.get('id')))
                elif type(obj) in self.DISPOSABLE_SYNAPSE_TYPES:
                    self.client.delete(obj)
                elif self._is_path(obj):
                    if os.path.isdir(obj):
                        os.rmdir(obj)
                    elif os.path.isfile(obj):
                        os.remove(obj)
                elif self._is_filehandle(obj):
                    self.client.restDELETE(uri='/fileHandle/{0}'.format(obj.get('id')),
                                           endpoint=self.client.fileHandleEndpoint)
            except Exception as ex:
                logging.warning('Could not delete: {0}, Error: {1}'.format(obj, str(ex)))

            if obj in self.trash:
                self.trash.remove(obj)

        return len(objects_to_dispose) == 0

    def _is_path(
            self,
            obj
    ) -> bool:
        """Gets if the object is a Path like object."""
        try:
            return obj is not None and PurePath(obj).is_absolute()
        except:
            return False

    __FILE_HANDLE__ATTRS__ = ['id',
                              'etag',
                              'createdBy',
                              'createdOn',
                              'modifiedOn',
                              'concreteType',
                              'contentType',
                              'contentMd5',
                              'fileName',
                              'storageLocationId',
                              'contentSize',
                              'status']

    def _is_filehandle(
            self,
            obj
    ) -> bool:
        """
        Gets if the object is a filehandle.
        https://rest-docs.synapse.org/rest/org/sagebionetworks/repo/model/file/FileHandle.html
        """
        return obj is not None and isinstance(obj, dict) and all(attr in obj for attr in self.__FILE_HANDLE__ATTRS__)

    def create_project(
            self,
            name: str = None,
            prefix: str = None,
            **kwargs
    ) -> synapseclient.Project:
        """Creates a new Project and adds it to the trash queue.

        Args:
            name: Name of the project. A unique name will be generated if not set. (optional)
            prefix: Prefix to add to the generated project name if the name arg is None. (optional)
            **kwargs:

        Returns:
            Project
        """
        kwargs['name'] = name if name else self.uniq_name(prefix=prefix)
        project = self.client.store(Project(**kwargs))
        self.dispose_of(project)
        return project

    def create_folder(
            self,
            name: str = None,
            prefix: str = None,
            parent: synapseclient.Project | synapseclient.Folder = None,
            **kwargs
    ) -> synapseclient.Folder:
        """Creates a new Folder and adds it to the trash queue.

        Args:
            name: Name of the folder. A unique name will be generated if not set. (optional)
            prefix: Prefix to add to the generated folder name if the name arg is None. (optional)
            parent: The Synapse parent container (Project or Folder). Will be created if not set. (optional)
            **kwargs:

        Returns:
            Folder
        """
        if 'parent' not in kwargs:
            if parent:
                kwargs['parent'] = parent
            else:
                logging.warning('Synapse folder parent not specified. Parent will be created.')
                kwargs['parent'] = self.create_project(prefix='Parent_For_Folder_')

        kwargs['name'] = name if name else self.uniq_name(prefix=prefix)

        folder = self.client.store(Folder(**kwargs))
        self.dispose_of(folder)
        return folder

    def create_file(
            self,
            name: str = None,
            path: str = None,
            parent: synapseclient.Project | synapseclient.Folder = None,
            **kwargs
    ) -> synapseclient.File:
        """Creates a new File and adds it to the trash queue.

        Args:
            name: Name of the file. (optional)
            path: Path to the file. Will be created if not set. (optional)
            parent: The Synapse parent container (Project or Folder). Will be created if not set. (optional)
            **kwargs:

        Returns:
            File
        """
        if 'parent' not in kwargs:
            if parent:
                kwargs['parent'] = parent
            else:
                logging.warning('Synapse file parent not specified. Parent will be created.')
                kwargs['parent'] = self.create_project(prefix='Parent_For_File_')

        if name:
            kwargs['name'] = name

        if 'path' not in kwargs:
            if path:
                kwargs['path'] = path
            else:
                logging.warning('Synapse file path not specified. Temporary file will be created.')
                kwargs['path'] = self.create_temp_file(name=name)

        file = self.client.store(File(**kwargs))
        self.dispose_of(file)
        return file

    def create_team(
            self,
            name: str = None,
            prefix: str = None,
            **kwargs
    ) -> synapseclient.Team:
        """
        Creates a new Team and adds it to the trash queue.

        Args:
            name: Name of the Team. A unique name will be generated if not set. (optional)
            prefix: Prefix to add to the generated team name if the name arg is None. (optional)

        Returns:
            Team
        """
        kwargs['name'] = name if name else self.uniq_name(prefix=prefix)
        team = self.client.store(Team(**kwargs))
        self.dispose_of(team)
        self.wait_for_team_to_be_available(team)
        return team

    def wait_for_team_to_be_available(
            self,
            team: synapseclient.Team
    ) -> synapseclient.Team:
        """Waits for a newly created team to be available in Synapse.
        There can be a delay from when a team is created and when syn.get() will return it.
        """
        tries = 0
        while True:
            tries += 1
            try:
                return self.client.getTeam(team.name)
                break
            except ValueError:
                if tries >= 10:
                    raise Exception('Timed out waiting for Team to be available in Synapse.')
                else:
                    time.sleep(3)

    def create_wiki(
            self,
            title: str = None,
            prefix: str = None,
            **kwargs
    ) -> synapseclient.Wiki:
        """
        Creates a new Wiki and adds it to the trash queue.

        Args:
            title: Title of the wiki. A unique name will be generated if not set. (optional)
            prefix: Prefix to add to the generated wiki title if the name arg is None. (optional)

        Returns:
            Wiki
        """
        kwargs['title'] = title if title else self.uniq_name(prefix=prefix)

        if 'markdown' not in kwargs:
            kwargs['markdown'] = 'My Wiki {0}'.format(kwargs['title'])

        wiki = self.client.store(Wiki(**kwargs))
        self.dispose_of(wiki)
        return wiki

    def create_temp_dir(
            self,
            name: str = None,
            suffix: str = None,
            prefix: str = None,
            dir: str = None
    ) -> str:
        """Creates a temp directory that will be disposed.

        Args:
            name: (optional)
            suffix: (optional)
            prefix: (optional)
            dir: (optional)

        Returns:
            Absolute path to the directory.
        """
        if name:
            if suffix:
                name += suffix
            if prefix:
                name = prefix + name

            dir = dir if dir else self.create_temp_dir()
            temp_dir = os.path.join(dir, name)
            os.makedirs(temp_dir, exist_ok=True)
        else:
            if dir:
                os.makedirs(dir, exist_ok=True)
            temp_dir = tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=dir)

        self.dispose_of(temp_dir)
        return temp_dir

    def create_temp_file(
            self,
            name: str = None,
            suffix: str = None,
            prefix: str = None,
            dir: str = None,
            content: str = None
    ) -> str:
        """Creates a temp file that will be disposed.
        If dir is not specified then a temp directory will be created and disposed too.

        Args:
            name: (optional)
            suffix: (optional)
            prefix: (optional)
            dir: (optional)
            content: (optional)

        Returns:
            Absolute path to the file.
        """
        dir = dir if dir else self.create_temp_dir()
        content = content if content else self.uniq_name()
        os.makedirs(dir, exist_ok=True)
        if name:
            if suffix:
                name += suffix
            if prefix:
                name = prefix + name

            tmp_filename = os.path.join(dir, name)
            with open(tmp_filename, 'w') as tmp:
                tmp.write(content)
        else:
            fd, tmp_filename = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
            with os.fdopen(fd, 'w') as tmp:
                tmp.write(content)

        self.dispose_of(tmp_filename)
        return tmp_filename
