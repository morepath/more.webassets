from __future__ import annotations

import os.path
import pytest
import tempfile
import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def tempdir() -> Generator[str]:
    directory = tempfile.mkdtemp()
    yield directory
    shutil.rmtree(directory)


@pytest.fixture
def current_path() -> str:
    return os.path.dirname(os.path.realpath(__file__))


@pytest.fixture
def fixtures_path(current_path: str) -> str:
    return os.path.join(current_path, "fixtures")
