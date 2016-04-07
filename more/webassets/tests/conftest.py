import os.path
import pytest
import tempfile
import shutil


@pytest.yield_fixture
def tempdir():
    directory = tempfile.mkdtemp()
    yield directory
    shutil.rmtree(directory)


@pytest.fixture
def current_path():
    return os.path.dirname(os.path.realpath(__file__))


@pytest.fixture
def fixtures_path(current_path):
    return os.path.join(current_path, 'fixtures')
