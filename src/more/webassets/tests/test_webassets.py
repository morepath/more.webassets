from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import pytest
from webtest import TestApp as Client

import more.webassets
import morepath
from more.webassets import WebassetsApp
from more.webassets.tweens import has_insecure_path_element, is_subpath

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

    from more.webassets.core import IncludeRequest


def utcnow() -> datetime:
    return datetime.now(UTC)


def symlink(source: str, link: str) -> None:
    try:
        os.symlink(source, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not supported")


def include_url(*bundles: str) -> str:
    """Returns a url that includes the given bundles, in the given order."""
    return "/include?" + urlencode([("bundle", bundle) for bundle in bundles])


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

    @App.view(model=Root, name="no-content")
    def no_content(self: Root, request: IncludeRequest) -> morepath.Response:
        request.include("common")
        return morepath.Response(status=204)

    @App.html(model=Root, name="alljs")
    def alljs(self: Root, request: IncludeRequest) -> str:
        request.include("common")
        request.include("extra")
        return html

    @App.html(model=Root, name="include")
    def include(self: Root, request: IncludeRequest) -> str:
        # includes every `bundle` query parameter, in the order given
        for bundle in request.params.getall("bundle"):
            if isinstance(bundle, str):
                request.include(bundle)

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


@pytest.mark.parametrize(
    ("included", "expected"),
    [
        # rendered in inclusion order, not alphabetical or registration order
        (["common", "extra"], ["common", "extra"]),
        (["extra", "common"], ["extra", "common"]),
        # including a bundle more than once is the same as including it once
        (["common", "common"], ["common"]),
        # re-including a bundle does not move it to the end
        (["extra", "common", "extra"], ["extra", "common"]),
        (["common", "extra", "common"], ["common", "extra"]),
    ],
)
def test_included_assets_order_and_deduplication(
    tempdir: str, included: list[str], expected: list[str]
) -> None:
    client = Client(spawn_test_app(tempdir))

    page = client.get(include_url(*included)).text
    scripts = re.findall(r'<script [^>]*src="(/assets/[^"?]+)', page)

    assert scripts == [f"/assets/{name}.bundle.js" for name in expected]


def test_included_assets_deduplicated_across_requests(tempdir: str) -> None:
    client = Client(spawn_test_app(tempdir))

    # every request gets its own, initially empty collection of assets
    first = client.get(include_url("extra")).text
    second = client.get(include_url("common")).text

    assert "extra.bundle.js" in first
    assert "common.bundle.js" not in first
    assert "common.bundle.js" in second
    assert "extra.bundle.js" not in second


def test_included_assets_deduplicated_stylesheets(tempdir: str) -> None:
    client = Client(spawn_test_app(tempdir))

    page = client.get(include_url("theme", "common", "theme")).text

    assert page.count("theme.bundle.css") == 1
    assert page.count("common.bundle.js") == 1
    # stylesheets are injected into the head, scripts at the end of the body
    assert page.find("theme.bundle.css") < page.find("common.bundle.js")


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


def test_publish_webassets_not_modified(tempdir: str) -> None:
    client = Client(spawn_test_app(tempdir))

    url = "/assets/common.bundle.js?ddc71aa3"

    client.get("?bundle=common")

    response = client.get(url)
    assert response.status_code == 200
    assert response.expires is not None

    # the long lived cache headers are only added to successful responses
    last_modified = response.headers["Last-Modified"]
    response = client.get(url, headers={"If-Modified-Since": last_modified})
    assert response.status_code == 304
    assert response.expires is None


def test_webassets_unhandled_content_type(tempdir: str) -> None:
    client = Client(spawn_test_app(tempdir))

    assert "<head></head>" in client.get("/plain").text


def test_webassets_unhandled_request_method(tempdir: str) -> None:
    client = Client(spawn_test_app(tempdir))

    assert "<head></head>" in client.put("/put").text


def test_webassets_response_without_content_type(tempdir: str) -> None:
    client = Client(spawn_test_app(tempdir))

    response = client.get("/no-content")

    assert response.status_code == 204
    assert response.body == b""


@pytest.mark.parametrize(
    "path",
    [
        # the path is unquoted a second time by the publisher
        "%252e%252e/secret.js",
        "%252e/secret.js",
        "common//jquery.js",
    ],
)
def test_publish_webassets_insecure_path(tempdir: str, path: str) -> None:
    client = Client(spawn_test_app(tempdir))

    with open(os.path.join(tempdir, "secret.js"), "w") as f:
        f.write("var secret = true;")

    assert client.get(f"/assets/{path}", expect_errors=True).status_code == 404


def test_publish_webassets_symlinked_directory(tempdir: str) -> None:
    client = Client(spawn_test_app(tempdir))

    outside = os.path.join(tempdir, "outside")
    os.mkdir(outside)

    with open(os.path.join(outside, "secret.js"), "w") as f:
        f.write("var secret = true;")

    symlink(outside, os.path.join(tempdir, "output", "link"))

    # files outside of the assets directory are not served, even if they are
    # reachable through a symlink inside of the assets directory
    response = client.get("/assets/link/secret.js", expect_errors=True)
    assert response.status_code == 404


def test_publish_webassets_symlinked_file(tempdir: str) -> None:
    client = Client(spawn_test_app(tempdir))

    output = os.path.join(tempdir, "output")

    with open(os.path.join(output, "real.js"), "w") as f:
        f.write("var real = true;")

    symlink(os.path.join(output, "real.js"), os.path.join(output, "linked.js"))

    assert client.get("/assets/real.js").text == "var real = true;"

    # symlinks are not served, even if they point to a file in the same directory
    assert client.get("/assets/linked.js", expect_errors=True).status_code == 404


def test_is_subpath(tempdir: str) -> None:
    assert is_subpath("/", "/test")
    assert is_subpath("/asdf", "/asdf/asdf")
    assert not is_subpath("/asdf/", "/asdf")
    assert not is_subpath("/a", "/b")
    assert not is_subpath("/a", "/a/../b")


def test_is_subpath_on_different_drives(monkeypatch: pytest.MonkeyPatch) -> None:
    # on Windows os.path.commonpath raises a ValueError for different drives
    def commonpath(paths: Iterable[str]) -> str:
        raise ValueError("Paths don't have the same drive")

    monkeypatch.setattr(os.path, "commonpath", commonpath)

    assert not is_subpath("/a", "/a/b")


def test_insecure_path_element() -> None:
    assert has_insecure_path_element("../test.txt")
    assert has_insecure_path_element("./test.txt")
    assert has_insecure_path_element("/test.txt")
    assert not has_insecure_path_element("test.txt")
    assert not has_insecure_path_element("asdf/asdf/test.txt")
