from __future__ import annotations

from collections.abc import Collection
from typing import Any, Protocol, TypeAlias

Filter: TypeAlias = Collection[str] | str


class AssetBundle(Protocol):
    """The part of :class:`webassets.bundle.Bundle` that we are using."""

    #: The file name of the bundle, which is written to the output directory.
    output: str

    #: The name of the bundle that has to be rendered after this bundle.
    #: We set it, if a js and a css bundle are registered under the same name.
    next_bundle: str

    def urls(self, *args: Any, **kwargs: Any) -> list[str]: ...


class AssetEnvironment(Protocol):
    """The part of :class:`webassets.env.Environment` that we are using."""

    debug: bool
    directory: str
    url: str

    def __getitem__(self, name: str) -> AssetBundle: ...

    def register(self, name: str, *args: Any, **kwargs: Any) -> Any: ...
