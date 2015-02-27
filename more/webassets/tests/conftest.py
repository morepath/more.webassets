import pytest
import tempfile
import shutil


@pytest.yield_fixture
def tempdir():
    directory = tempfile.mkdtemp()
    yield directory
    shutil.rmtree(directory)
