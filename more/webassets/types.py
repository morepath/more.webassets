from __future__ import annotations

from collections.abc import Collection
from typing import TypeAlias

Filter: TypeAlias = Collection[str] | str
