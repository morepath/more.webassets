from __future__ import annotations

import os.path
from typing import TYPE_CHECKING

import pytest

import morepath
from more.webassets import WebassetsApp
from more.webassets.directives import Asset, WebassetRegistry

if TYPE_CHECKING:
    from collections.abc import Generator


def test_webasset_path(current_path: str) -> None:
    current_path = os.path.dirname(os.path.realpath(__file__))

    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_path() -> str:
        return "./fixtures"

    @App.webasset_path()
    def get_overlapping_path() -> str:
        return os.path.join(current_path, "./fixtures")

    @App.webasset_path()
    def get_current_path() -> str:
        return "."

    @App.webasset_path()
    def get_parent_path() -> str:
        return ".."

    morepath.commit(App)

    app = App()

    assert app.config.webasset_registry.paths == [
        os.path.normpath(os.path.join(current_path, "..")),
        os.path.normpath(os.path.join(current_path, ".")),
        os.path.normpath(os.path.join(current_path, "fixtures")),
        os.path.normpath(os.path.join(current_path, "fixtures")),
    ]


def test_webasset_relative(current_path: str) -> None:
    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_relative_path() -> str:
        return "fixtures"

    morepath.commit(App)

    assert App().config.webasset_registry.paths == [
        os.path.join(current_path, "fixtures")
    ]


def test_webasset_path_inheritance(tempdir: str, current_path: str) -> None:
    os.mkdir(os.path.join(tempdir, "A"))
    os.mkdir(os.path.join(tempdir, "B"))
    os.mkdir(os.path.join(tempdir, "C"))

    class A(WebassetsApp):
        pass

    @A.webasset_path()
    def get_path_a() -> str:
        return os.path.join(tempdir, "A")

    class B(WebassetsApp):
        pass

    @B.webasset_path()
    def get_path_b() -> str:
        return os.path.join(tempdir, "B")

    class C(B, A):
        pass

    @C.webasset_path()
    def get_path_c() -> str:
        return os.path.join(tempdir, "C")

    class D(A, B):
        pass

    @D.webasset_path()
    def get_path_c_2() -> str:
        return os.path.join(tempdir, "C")

    # the order of A and B is defined by the order they are scanned with
    morepath.commit(A, B, C, D)

    assert C().config.webasset_registry.paths == [
        os.path.join(tempdir, "C"),
        os.path.join(tempdir, "B"),
        os.path.join(tempdir, "A"),
    ]

    assert D().config.webasset_registry.paths == [
        os.path.join(tempdir, "C"),
        os.path.join(tempdir, "B"),
        os.path.join(tempdir, "A"),
    ]


def test_webasset_filter() -> None:
    class Base(WebassetsApp):
        pass

    @Base.webasset_filter("js")
    def get_base_js_filter() -> str:
        return "jsmin"

    class App(WebassetsApp):
        pass

    @App.webasset_filter("js")
    def get_js_filter() -> str:
        return "rjsmin"

    morepath.commit(App)

    assert App().config.webasset_registry.filters == {"js": "rjsmin"}


def test_webasset_filter_chain(fixtures_path: str) -> None:
    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_path() -> str:
        return fixtures_path

    @App.webasset_filter("js", produces="css")
    def foo_filter() -> str:
        return "jsmin"

    @App.webasset_filter("css")
    def bar_filter() -> str:
        return "cssmin"

    @App.webasset("common")
    def get_common_assets() -> Generator[str]:
        yield "jquery.js"

    morepath.commit(App)

    common = list(App().config.webasset_registry.get_bundles("common"))
    assert len(common) == 1
    assert common[0].filters[0].name == "jsmin"
    assert common[0].filters[1].name == "cssmin"


def test_webasset_directive(tempdir: str, fixtures_path: str) -> None:
    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_path() -> str:
        return fixtures_path

    @App.webasset_output()
    def get_output_path() -> str:
        return tempdir

    @App.webasset("common")
    def get_common_assets() -> Generator[str]:
        yield "jquery.js"
        yield "underscore.js"

    morepath.commit(App)

    app = App()

    assert app.config.webasset_registry.assets == {
        "jquery.js": Asset(
            name="jquery.js",
            assets=(os.path.join(fixtures_path, "jquery.js"),),
            filters={},
        ),
        "underscore.js": Asset(
            name="underscore.js",
            assets=(os.path.join(fixtures_path, "underscore.js"),),
            filters={},
        ),
        "common": Asset(
            name="common", assets=("jquery.js", "underscore.js"), filters={}
        ),
    }

    common = list(app.config.webasset_registry.get_bundles("common"))

    assert len(common) == 1
    assert common[0].output.endswith("common.bundle.js")
    assert common[0].contents == (
        os.path.join(fixtures_path, "jquery.js"),
        os.path.join(fixtures_path, "underscore.js"),
    )

    jquery = list(app.config.webasset_registry.get_bundles("jquery.js"))

    assert len(jquery) == 1
    assert jquery[0].output.endswith("jquery.js.bundle.js")
    assert jquery[0].contents == (os.path.join(fixtures_path, "jquery.js"),)

    underscore = list(app.config.webasset_registry.get_bundles("underscore.js"))

    assert len(underscore) == 1
    assert underscore[0].output.endswith("underscore.js.bundle.js")
    assert underscore[0].contents == (os.path.join(fixtures_path, "underscore.js"),)


def test_webasset_override_filters(tempdir: str, fixtures_path: str) -> None:
    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_path() -> str:
        return fixtures_path

    @App.webasset_output()
    def get_output_path() -> str:
        return tempdir

    @App.webasset("jquery")
    def get_jquery_asset() -> Generator[str]:
        yield "jquery.js"

    @App.webasset_filter("js")
    def get_js_filter() -> str:
        return "rjsmin"

    class DebugApp(App):
        pass

    @DebugApp.webasset_filter("js")
    def get_debug_js_filter() -> None:
        return None

    morepath.commit(DebugApp, App)

    bundles = list(App().config.webasset_registry.get_bundles("jquery"))
    assert len(bundles) == 1
    assert bundles[0].filters[0].name == "rjsmin"

    bundles = list(DebugApp().config.webasset_registry.get_bundles("jquery"))
    assert len(bundles) == 1
    assert not bundles[0].filters


def test_webasset_override_filter_through_bundle(
    tempdir: str, fixtures_path: str
) -> None:
    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_path() -> str:
        return fixtures_path

    @App.webasset_output()
    def get_output_path() -> str:
        return tempdir

    @App.webasset("jquery")
    def get_jquery_asset() -> Generator[str]:
        yield "jquery.js"

    @App.webasset_filter("js")
    def get_js_filter() -> str:
        return "rjsmin"

    class DebugApp(App):
        pass

    @DebugApp.webasset("common", filters={"js": None})
    def get_debug_js_filter() -> Generator[str]:
        yield "jquery"

    morepath.commit(DebugApp, App)

    bundles = list(App().config.webasset_registry.get_bundles("jquery"))
    assert len(bundles) == 1
    assert bundles[0].filters[0].name == "rjsmin"

    bundles = list(DebugApp().config.webasset_registry.get_bundles("common"))
    assert len(bundles) == 1
    assert not bundles[0].filters


def test_global_filter_is_only_a_default(tempdir: str, fixtures_path: str) -> None:
    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_path() -> str:
        return fixtures_path

    @App.webasset_output()
    def get_output_path() -> str:
        return tempdir

    @App.webasset("jquery", filters={"js": None})
    def get_jquery_asset() -> Generator[str]:
        yield "jquery.js"

    @App.webasset_filter("js")
    def get_js_filter() -> str:
        return "rjsmin"

    morepath.commit(App)

    bundles = list(App().config.webasset_registry.get_bundles("jquery"))
    assert len(bundles) == 1
    assert not bundles[0].filters


def test_global_filter_is_only_a_default_with_bundle(
    tempdir: str, fixtures_path: str
) -> None:
    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_path() -> str:
        return fixtures_path

    @App.webasset_output()
    def get_output_path() -> str:
        return tempdir

    @App.webasset("jquery", filters={"js": None})
    def get_jquery_asset() -> Generator[str]:
        yield "jquery.js"

    @App.webasset("common")
    def get_common_asset() -> Generator[str]:
        yield "jquery"

    @App.webasset_filter("js")
    def get_js_filter() -> str:
        return "rjsmin"

    morepath.commit(App)

    bundles = list(App().config.webasset_registry.get_bundles("common"))
    assert len(bundles) == 1
    assert not bundles[0].filters

    bundles = list(App().config.webasset_registry.get_bundles("jquery"))
    assert len(bundles) == 1
    assert not bundles[0].filters


def test_webasset_mixed_bundles(tempdir: str, fixtures_path: str) -> None:
    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_path() -> str:
        return fixtures_path

    @App.webasset_output()
    def get_output_path() -> str:
        return tempdir

    @App.webasset("common")
    def get_jquery_asset() -> Generator[str]:
        yield "jquery.js"
        yield "extra.css"

    morepath.commit(App)

    bundles = list(App().config.webasset_registry.get_bundles("common"))
    assert len(bundles) == 2

    assert bundles[0].output.endswith("jquery.js.bundle.js")
    assert bundles[0].contents == (os.path.join(fixtures_path, "jquery.js"),)

    assert bundles[1].output.endswith("extra.css.bundle.css")
    assert bundles[1].contents == (os.path.join(fixtures_path, "extra.css"),)


def test_webasset_compiled_bundle(tempdir: str, fixtures_path: str) -> None:
    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_path() -> str:
        return fixtures_path

    @App.webasset_output()
    def get_output_path() -> str:
        return tempdir

    @App.webasset_filter("scss")
    def get_scss_filter() -> str:
        return "libsass"

    @App.webasset("theme")
    def get_jquery_asset() -> Generator[str]:
        yield "main.scss"
        yield "extra.css"

    morepath.commit(App)

    bundles = list(App().config.webasset_registry.get_bundles("theme"))
    assert len(bundles) == 2

    assert bundles[0].output.endswith("main.scss.bundle.css")
    assert bundles[0].contents == (os.path.join(fixtures_path, "main.scss"),)

    assert bundles[1].output.endswith("extra.css.bundle.css")
    assert bundles[1].contents == (os.path.join(fixtures_path, "extra.css"),)


def test_webasset_environment(tempdir: str, fixtures_path: str) -> None:
    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_path() -> str:
        return fixtures_path

    @App.webasset_output()
    def get_output_path() -> str:
        return tempdir

    @App.webasset_filter("scss")
    def get_scss_filter() -> str:
        return "libsass"

    @App.webasset("js")
    def get_js_asset() -> Generator[str]:
        yield "jquery.js"
        yield "underscore.js"

    @App.webasset("css")
    def get_css_asset() -> Generator[str]:
        yield "main.scss"
        yield "extra.css"

    @App.webasset("common")
    def get_common_assets() -> Generator[str]:
        yield "js"
        yield "css"

    morepath.commit(App)

    e = App().config.webasset_registry.get_environment()

    for asset in ("jquery.js", "underscore.js"):
        assert e[asset].output.endswith(f"{asset}.bundle.js")
        assert e[asset].contents == (os.path.join(fixtures_path, asset),)
        assert len(e[asset].urls()) == 1

    for asset in ("main.scss", "extra.css"):
        assert e[asset].output.endswith(f"{asset}.bundle.css")
        assert e[asset].contents == (os.path.join(fixtures_path, asset),)
        assert len(e[asset].urls()) == 1

    assert e["js"].output.endswith("js.bundle.js")
    assert e["js"].contents == (
        os.path.join(fixtures_path, "jquery.js"),
        os.path.join(fixtures_path, "underscore.js"),
    )

    assert len(e["js"].urls()) == 1

    assert e["css"].output.endswith("css.bundle.css")
    assert len(e["css"].contents) == 2
    assert e["css"].contents[0].output.endswith("main.scss.bundle.css")
    assert e["css"].contents[0].contents == (os.path.join(fixtures_path, "main.scss"),)

    assert e["css"].contents[1].output.endswith("extra.css.bundle.css")
    assert e["css"].contents[1].contents == (os.path.join(fixtures_path, "extra.css"),)

    assert len(e["css"].urls()) == 1

    assert e["common"].output.endswith("js.bundle.js")
    assert e["common"].contents == e["js"].contents
    assert len(e["common"].urls()) == 1

    assert e["common_1"].contents[0].output == e["css"].contents[0].output
    assert e["common_1"].contents[0].contents == e["css"].contents[0].contents
    assert e["common_1"].contents[1].output == e["css"].contents[1].output
    assert e["common_1"].contents[1].contents == e["css"].contents[1].contents
    assert len(e["common_1"].urls()) == 1


def test_webasset_output_relative(current_path: str) -> None:
    class App(WebassetsApp):
        pass

    @App.webasset_output()
    def get_output_path() -> str:
        return "bundles"

    morepath.commit(App)

    assert App().config.webasset_registry.output_path == os.path.join(
        current_path, "bundles"
    )


def test_webasset_mapping() -> None:
    class App(WebassetsApp):
        pass

    @App.webasset_mapping("mjs")
    def get_mjs_mapping() -> str:
        return "js"

    morepath.commit(App)

    mapping = App().config.webasset_registry.mapping

    assert mapping["mjs"] == "js"
    # the default mappings are kept
    assert mapping["scss"] == "css"


def test_webasset_url() -> None:
    class App(WebassetsApp):
        pass

    @App.webasset_url()
    def get_url() -> str:
        return "my-assets"

    morepath.commit(App)

    registry = App().config.webasset_registry

    assert registry.url == "my-assets"
    assert registry.get_environment().url == "my-assets"


def test_asset_extension() -> None:
    assert Asset("scripts", ["a.js", "b.js"], None).extension == "js"
    assert Asset("mixed", ["a.js", "b.css"], None).extension is None


def test_find_file_absolute_path(fixtures_path: str) -> None:
    path = os.path.join(fixtures_path, "jquery.js")

    # absolute paths are returned as they are, without searching for them
    assert WebassetRegistry().find_file(path) == path


def test_find_file_searches_each_path_once(
    tempdir: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = WebassetRegistry()
    # the same path may be registered more than once
    registry.paths = [tempdir, tempdir]

    searched: list[str] = []

    def isfile(path: str) -> bool:
        searched.append(path)
        return False

    monkeypatch.setattr(os.path, "isfile", isfile)

    with pytest.raises(LookupError, match=r"Could not find missing\.js in paths"):
        registry.find_file("missing.js")

    assert searched == [os.path.join(tempdir, "missing.js")]


def test_get_asset_filters_of_mixed_asset() -> None:
    registry = WebassetRegistry()
    registry.register_filter("js", "rjsmin")

    mixed = Asset("mixed", ["a.js", "b.css"], None)

    assert registry.get_asset_filters(mixed, registry.filters) is None


def test_get_asset_filters_with_multiple_filters() -> None:
    registry = WebassetRegistry()
    registry.register_filter("js", ["jsmin", "rjsmin"])

    asset = Asset("scripts", ["a.js"], None)

    assert registry.get_asset_filters(asset, registry.filters) == [
        "jsmin",
        "rjsmin",
    ]
