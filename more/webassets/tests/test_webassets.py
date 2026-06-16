from __future__ import annotations

import more.webassets
import morepath
import os
import pytest

from datetime import datetime, timezone
from more.webassets import WebassetsApp
from more.webassets.tweens import is_subpath, has_insecure_path_element
from typing import TYPE_CHECKING
from webtest import TestApp as Client

if TYPE_CHECKING:
    from collections.abc import Generator
    from more.webassets.core import IncludeRequest


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def prepare_fixtures(directory: str) -> None:
    os.mkdir(os.path.join(directory, "common"))
    os.mkdir(os.path.join(directory, "output"))
    os.mkdir(os.path.join(directory, "theme"))

    # if those javascripts are changed, the tests below need to be updated
    # with the correct md5 hashes
    with open(os.path.join(directory, "common", "jquery.js"), "w") as f:
        f.write("""
            /* fake jquery */
            var $ = function(){};
        """)

    with open(os.path.join(directory, "common", "underscore.js"), "w") as f:
        f.write("""
            /* fake underscore */
            var _ = function(){};
        """)

    with open(os.path.join(directory, "theme", "main.scss"), "w") as f:
        f.write("""
            body {
                a {
                    color: blue;
                }
            }
        """)

    with open(os.path.join(directory, "theme", "other.css"), "w") as f:
        f.write("""
            h1 {
                font-size: 2rem;
            }
        """)

    with open(os.path.join(directory, "common", "extra.js"), "w") as f:
        f.write("""
            $(document).ready(function(){});
        """)


def spawn_test_app(tempdir: str) -> WebassetsApp:
    prepare_fixtures(tempdir)

    html = """
        <html>
            <head></head>
            <body>
                <p>Bar</p>
            </body>
        </html>
    """

    def render_plain(content: str, request: morepath.Request) -> morepath.Response:
        response = morepath.Response(content)
        response.content_type = "text/plain"
        return response

    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_default_assets_path() -> str:
        return os.path.join(tempdir, "common")

    @App.webasset_path()
    def get_theme_assets_path() -> str:
        return os.path.join(tempdir, "theme")

    @App.webasset_output()
    def get_output_path() -> str:
        return os.path.join(tempdir, "output")

    @App.webasset_filter("js")
    def get_js_filter() -> str:
        return "rjsmin"

    @App.webasset_filter("scss")
    def get_scss_filter() -> str:
        return "libsass"

    @App.webasset(name="common")
    def get_common_assets() -> Generator[str]:
        yield "jquery.js"
        yield "underscore.js"

    @App.webasset(name="extra")
    def get_extra_asset() -> Generator[str]:
        yield "extra.js"

    @App.webasset(name="theme")
    def get_theme_asset() -> Generator[str]:
        yield "main.scss"

    @App.path("")
    class Root:
        pass

    @App.html(model=Root)
    def index(self: Root, request: IncludeRequest) -> str:
        bundle = request.params.get("bundle")

        if bundle and isinstance(bundle, str):
            request.include(bundle)

        return html

    @App.view(model=Root, name="plain", render=render_plain)
    def plain(self: Root, request: IncludeRequest) -> str:
        request.include("common")
        return html

    @App.html(model=Root, name="put", request_method="PUT")
    def put(self: Root, request: IncludeRequest) -> str:
        request.include("common")
        return html

    @App.html(model=Root, name="alljs")
    def alljs(self: Root, request: IncludeRequest) -> str:
        request.include("common")
        request.include("extra")
        return html

    morepath.scan(more.webassets)
    morepath.commit(App)

    return App()


def test_inject_webassets(tempdir: str) -> None:
    client = Client(spawn_test_app(tempdir))

    assert "<head></head>" in client.get("/").text

    with pytest.raises(KeyError):
        assert "<head></head>" in client.get("?bundle=inexistant").text

    # the version of these assets stays the same because it's basically the
    # md5 hash of the javascript files included
    injected_html = (
        '<script type="text/javascript" '
        'src="/assets/common.bundle.js?ddc71aa3"></script></body>'
    )

    assert injected_html in client.get("?bundle=common").text

    injected_html = (
        '<link rel="stylesheet" type="text/css" '
        'href="/assets/theme.bundle.css?32fda411"></head>'
    )

    assert injected_html in client.get("?bundle=theme").text

    page = client.get("/alljs").text
    assert page.find("common.bundle.js") < page.find("extra.bundle.js")


def test_publish_webassets(tempdir: str) -> None:
    client = Client(spawn_test_app(tempdir))

    url = "/assets/common.bundle.js?ddc71aa3"

    # before the urls() have not been called by the injector, the bundles
    # won't have been created
    assert client.get(url, expect_errors=True).status_code == 404

    client.get("?bundle=common")

    response = client.get(url)
    assert response.text == "var $=function(){};var _=function(){};"
    assert response.expires is not None
    assert response.expires.year == utcnow().year + 10
    assert response.content_type == "text/javascript"

    # do the same for css
    url = "/assets/theme.bundle.css?32fda411"

    assert client.get(url, expect_errors=True).status_code == 404

    client.get("?bundle=theme")

    response = client.get(url)
    assert response.text == "body a {\n  color: blue; }\n"
    assert response.expires is not None
    assert response.expires.year == utcnow().year + 10
    assert response.content_type == "text/css"


def test_webassets_unhandled_content_type(tempdir: str) -> None:
    client = Client(spawn_test_app(tempdir))

    assert "<head></head>" in client.get("/plain").text


def test_webassets_unhandled_request_method(tempdir: str) -> None:
    client = Client(spawn_test_app(tempdir))

    assert "<head></head>" in client.put("/put").text


def test_is_subpath(tempdir: str) -> None:
    assert is_subpath("/", "/test")
    assert is_subpath("/asdf", "/asdf/asdf")
    assert not is_subpath("/asdf/", "/asdf")
    assert not is_subpath("/a", "/b")
    assert not is_subpath("/a", "/a/../b")


def test_insecure_path_element() -> None:
    assert has_insecure_path_element("../test.txt")
    assert has_insecure_path_element("./test.txt")
    assert has_insecure_path_element("/test.txt")
    assert not has_insecure_path_element("test.txt")
    assert not has_insecure_path_element("asdf/asdf/test.txt")
