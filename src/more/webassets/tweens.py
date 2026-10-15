from __future__ import annotations

import os
import time
from datetime import timedelta
from typing import TYPE_CHECKING
from urllib.parse import unquote

import webob.exc
from webob.static import FileApp

if TYPE_CHECKING:
    from collections.abc import Generator

    from webassets.env import Environment
    from webob import Response as BaseResponse

    from morepath.request import Request
    from morepath.types import StrPath, Tween

    from .core import IncludeRequest


# content types and methods that get handled by the injector/publisher
CONTENT_TYPES = {"text/html", "application/xhtml+xml"}
METHODS = {"GET", "POST", "HEAD"}

# arbitrarily define forever as 10 years in the future
FOREVER = int(timedelta(days=365 * 10).total_seconds())


# what separators does this operating system provide that are not a slash?
_os_alt_seps = {sep for sep in [os.path.sep, os.path.altsep] if sep not in (None, "/")}

# what elements may not be in a path element?
_insecure_elements = {"..", ".", ""} | _os_alt_seps


def is_subpath(directory: StrPath, path: StrPath) -> bool:
    """Returns true if the given path is inside the given directory."""
    directory = os.path.join(os.path.realpath(directory), "")
    path = os.path.realpath(path)

    # return true, if the common prefix of both is equal to directory
    # e.g. /a/b/c/d.rst and directory is /a/b, the common prefix is /a/b
    return os.path.commonprefix([path, directory]) == directory


def has_insecure_path_element(path: str) -> bool:
    """Returns true if the given path contains an insecure path element.
    That is '..' or '.' or ''
    """
    if _insecure_elements.intersection(path.split("/")):
        return True

    return False


class InjectorTween:
    """Injects the webasset urls into the response."""

    def __init__(self, environment: Environment, handler: Tween) -> None:
        self.environment = environment
        self.handler = handler
        self._urls: dict[str, list[str]] = {}

    def urls_by_resource(self, resource: str) -> list[str]:
        if self.environment.debug or resource not in self._urls:
            self._urls[resource] = []

            bundle = self.environment[resource]
            while bundle is not None:
                self._urls[resource].extend(bundle.urls())

                try:
                    bundle = self.environment[getattr(bundle, "next_bundle")]
                except (AttributeError, KeyError):
                    bundle = None

        return self._urls[resource]

    def urls_to_inject(
        self, request: IncludeRequest, suffix: str | None = None
    ) -> Generator[str]:
        for resource in request.included_assets:
            for url in self.urls_by_resource(resource):
                filename = url.split("?")[0]

                if suffix and not filename.endswith(suffix):
                    continue

                yield "/" + url

    def __call__(self, request: IncludeRequest) -> BaseResponse:
        response = self.handler(request)

        if request.method not in METHODS:
            return response

        if not response.content_type:  # may be None if the code is != 200
            return response

        if response.content_type.lower() not in CONTENT_TYPES:
            return response

        scripts = "\n".join(
            f'<script type="text/javascript" src="{url}"></script>'
            for url in self.urls_to_inject(request, ".js")
        )

        stylesheets = "\n".join(
            f'<link rel="stylesheet" type="text/css" href="{url}">'
            for url in self.urls_to_inject(request, ".css")
        )

        if scripts:
            response.body = response.body.replace(
                b"</body>", scripts.encode("utf-8") + b"</body>", 1
            )

        if stylesheets:
            response.body = response.body.replace(
                b"</head>", stylesheets.encode("utf-8") + b"</head>", 1
            )

        return response


class PublisherTween:
    """Returns the webassets if the request begins with the
    :attr:`WebassetsApp.webassets_url`.

    """

    def __init__(self, environment: Environment, handler: Tween) -> None:
        self.environment = environment
        self.handler = handler

    def __call__(self, request: Request) -> BaseResponse:
        publisher_signature = request.path_info_peek()

        if publisher_signature != self.environment.url:
            return self.handler(request)

        assert publisher_signature is not None
        subpath = request.path_info.replace(publisher_signature, "").strip("/")
        subpath = unquote(subpath)

        if has_insecure_path_element(subpath):
            return webob.exc.HTTPNotFound()

        asset = os.path.join(self.environment.directory, subpath)
        asset = os.path.abspath(asset)

        # I'm not entirely at ease with loading a file from disk and returning
        # it over the web. So as an extra precaution I want to make sure
        # that only files *inside* the assets folder will be served.
        #
        # I doubt webob let's this happen, but if somebody is ever able to
        # create an url resulting in a path that points outside the assets
        # directory this check might help.
        if not is_subpath(self.environment.directory, asset):
            return webob.exc.HTTPNotFound()

        # This is possibly too paranoid
        if os.path.islink(asset):
            return webob.exc.HTTPNotFound()

        if not os.path.isfile(asset):
            return webob.exc.HTTPNotFound()

        response = request.get_response(FileApp(asset))

        if response.status_code == 200:
            response.cache_control.max_age = FOREVER
            response.expires = time.time() + FOREVER

        return response
