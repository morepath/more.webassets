import morepath
import os.path

from more.webassets import WebassetsApp
from more.webassets.directives import Asset


def test_webasset_path(current_path):

    current_path = os.path.dirname(os.path.realpath(__file__))

    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_path():
        return './fixtures'

    @App.webasset_path()
    def get_overlapping_path():
        return os.path.join(current_path, './fixtures')

    @App.webasset_path()
    def get_current_path():
        return '.'

    @App.webasset_path()
    def get_parent_path():
        return '..'

    morepath.commit(App)

    app = App()

    assert app.config.webasset_registry.paths == [
        os.path.normpath(os.path.join(current_path, '..')),
        os.path.normpath(os.path.join(current_path, '.')),
        os.path.normpath(os.path.join(current_path, 'fixtures')),
        os.path.normpath(os.path.join(current_path, 'fixtures')),
    ]


def test_webasset_relative(current_path):

    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_relative_path():
        return 'fixtures'

    morepath.commit(App)

    assert App().config.webasset_registry.paths == [
        os.path.join(current_path, 'fixtures')
    ]


def test_webasset_path_inheritance(tempdir, current_path):

    os.mkdir(os.path.join(tempdir, 'A'))
    os.mkdir(os.path.join(tempdir, 'B'))
    os.mkdir(os.path.join(tempdir, 'C'))

    class A(WebassetsApp):
        pass

    @A.webasset_path()
    def get_path_a():
        return os.path.join(tempdir, 'A')

    class B(WebassetsApp):
        pass

    @B.webasset_path()
    def get_path_b():
        return os.path.join(tempdir, 'B')

    class C(B, A):
        pass

    @C.webasset_path()
    def get_path_c():
        return os.path.join(tempdir, 'C')

    class D(A, B):
        pass

    @D.webasset_path()
    def get_path_c_2():
        return os.path.join(tempdir, 'C')

    # the order of A and B is defined by the order they are scanned with
    morepath.commit(A, B, C, D)

    assert C().config.webasset_registry.paths == [
        os.path.join(tempdir, 'C'),
        os.path.join(tempdir, 'B'),
        os.path.join(tempdir, 'A'),
    ]

    assert D().config.webasset_registry.paths == [
        os.path.join(tempdir, 'C'),
        os.path.join(tempdir, 'B'),
        os.path.join(tempdir, 'A'),
    ]


def test_webasset_filter():

    class Base(WebassetsApp):
        pass

    @Base.webasset_filter('js')
    def get_base_js_filter():
        return 'jsmin'

    class App(WebassetsApp):
        pass

    @App.webasset_filter('js')
    def get_js_filter():
        return 'rjsmin'

    morepath.commit(App)

    assert App().config.webasset_registry.filters == {'js': 'rjsmin'}


def test_webasset_directive(tempdir, fixtures_path):

    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_path():
        return fixtures_path

    @App.webasset_output()
    def get_output_path():
        return tempdir

    @App.webasset('common')
    def get_common_assets():
        yield 'jquery.js'
        yield 'underscore.js'

    morepath.commit(App)

    app = App()

    assert app.config.webasset_registry.assets == {
        'jquery.js': Asset(
            name='jquery.js',
            assets=(os.path.join(fixtures_path, 'jquery.js'), ),
            filters={}
        ),
        'underscore.js': Asset(
            name='underscore.js',
            assets=(os.path.join(fixtures_path, 'underscore.js'), ),
            filters={}
        ),
        'common': Asset(
            name='common',
            assets=('jquery.js', 'underscore.js'),
            filters={}
        )
    }

    common = list(app.config.webasset_registry.get_bundles('common'))

    assert len(common) == 1
    assert common[0].output.endswith('common.bundle.js')
    assert common[0].contents == (
        os.path.join(fixtures_path, 'jquery.js'),
        os.path.join(fixtures_path, 'underscore.js')
    )

    jquery = list(app.config.webasset_registry.get_bundles('jquery.js'))

    assert len(jquery) == 1
    assert jquery[0].output.endswith('jquery.js.bundle.js')
    assert jquery[0].contents == (
        os.path.join(fixtures_path, 'jquery.js'),
    )

    underscore = list(
        app.config.webasset_registry.get_bundles('underscore.js'))

    assert len(underscore) == 1
    assert underscore[0].output.endswith('underscore.js.bundle.js')
    assert underscore[0].contents == (
        os.path.join(fixtures_path, 'underscore.js'),
    )


def test_webasset_override_filters(tempdir, fixtures_path):

    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_path():
        return fixtures_path

    @App.webasset_output()
    def get_output_path():
        return tempdir

    @App.webasset('jquery')
    def get_jquery_asset():
        yield 'jquery.js'

    @App.webasset_filter('js')
    def get_js_filter():
        return 'rjsmin'

    class DebugApp(App):
        pass

    @DebugApp.webasset_filter('js')
    def get_debug_js_filter():
        return None

    morepath.commit(DebugApp, App)

    bundles = list(App().config.webasset_registry.get_bundles('jquery'))
    assert len(bundles) == 1
    assert bundles[0].filters[0].name == 'rjsmin'

    bundles = list(DebugApp().config.webasset_registry.get_bundles('jquery'))
    assert len(bundles) == 1
    assert not bundles[0].filters


def test_webasset_override_filter_through_bundle(tempdir, fixtures_path):

    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_path():
        return fixtures_path

    @App.webasset_output()
    def get_output_path():
        return tempdir

    @App.webasset('jquery')
    def get_jquery_asset():
        yield 'jquery.js'

    @App.webasset_filter('js')
    def get_js_filter():
        return 'rjsmin'

    class DebugApp(App):
        pass

    @DebugApp.webasset('common', filters={'js': None})
    def get_debug_js_filter():
        yield 'jquery'

    morepath.commit(DebugApp, App)

    bundles = list(App().config.webasset_registry.get_bundles('jquery'))
    assert len(bundles) == 1
    assert bundles[0].filters[0].name == 'rjsmin'

    bundles = list(DebugApp().config.webasset_registry.get_bundles('common'))
    assert len(bundles) == 1
    assert not bundles[0].filters


def test_webasset_mixed_bundles(tempdir, fixtures_path):

    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_path():
        return fixtures_path

    @App.webasset_output()
    def get_output_path():
        return tempdir

    @App.webasset('common')
    def get_jquery_asset():
        yield 'jquery.js'
        yield 'extra.css'

    morepath.commit(App)

    bundles = list(App().config.webasset_registry.get_bundles('common'))
    assert len(bundles) == 2

    assert bundles[0].output.endswith('jquery.js.bundle.js')
    assert bundles[0].contents == (
        os.path.join(fixtures_path, 'jquery.js'),
    )

    assert bundles[1].output.endswith('extra.css.bundle.css')
    assert bundles[1].contents == (
        os.path.join(fixtures_path, 'extra.css'),
    )


def test_webasset_compiled_bundle(tempdir, fixtures_path):

    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_path():
        return fixtures_path

    @App.webasset_output()
    def get_output_path():
        return tempdir

    @App.webasset_filter('scss')
    def get_scss_filter():
        return 'pyscss'

    @App.webasset('theme')
    def get_jquery_asset():
        yield 'main.scss'
        yield 'extra.css'

    morepath.commit(App)

    bundles = list(App().config.webasset_registry.get_bundles('theme'))
    assert len(bundles) == 2

    assert bundles[0].output.endswith('main.scss.bundle.css')
    assert bundles[0].contents == (
        os.path.join(fixtures_path, 'main.scss'),
    )

    assert bundles[1].output.endswith('extra.css.bundle.css')
    assert bundles[1].contents == (
        os.path.join(fixtures_path, 'extra.css'),
    )


def test_webasset_environment(tempdir, fixtures_path):

    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_path():
        return fixtures_path

    @App.webasset_output()
    def get_output_path():
        return tempdir

    @App.webasset_filter('scss')
    def get_scss_filter():
        return 'pyscss'

    @App.webasset('js')
    def get_js_asset():
        yield 'jquery.js'
        yield 'underscore.js'

    @App.webasset('css')
    def get_css_asset():
        yield 'main.scss'
        yield 'extra.css'

    @App.webasset('common')
    def get_common_assets():
        yield 'js'
        yield 'css'

    morepath.commit(App)

    e = App().config.webasset_registry.get_environment()

    for asset in ('jquery.js', 'underscore.js'):
        assert e[asset].output.endswith('{}.bundle.js'.format(asset))
        assert e[asset].contents == (os.path.join(fixtures_path, asset),)
        assert len(e[asset].urls()) == 1

    for asset in ('main.scss', 'extra.css'):
        assert e[asset].output.endswith('{}.bundle.css'.format(asset))
        assert e[asset].contents == (os.path.join(fixtures_path, asset),)
        assert len(e[asset].urls()) == 1

    assert e['js'].output.endswith('js.bundle.js')
    assert e['js'].contents == (
        os.path.join(fixtures_path, 'jquery.js'),
        os.path.join(fixtures_path, 'underscore.js'),
    )

    assert len(e['js'].urls()) == 1

    assert e['css'].output.endswith('css.bundle.css')
    assert len(e['css'].contents) == 2
    assert e['css'].contents[0].output.endswith('main.scss.bundle.css')
    assert e['css'].contents[0].contents == (
        os.path.join(fixtures_path, 'main.scss'),
    )

    assert e['css'].contents[1].output.endswith('extra.css.bundle.css')
    assert e['css'].contents[1].contents == (
        os.path.join(fixtures_path, 'extra.css'),
    )

    assert len(e['css'].urls()) == 1

    assert e['common'].output.endswith('js.bundle.js')
    assert e['common'].contents == e['js'].contents
    assert len(e['common'].urls()) == 1

    assert e['common_1'].contents[0].output == e['css'].contents[0].output
    assert e['common_1'].contents[0].contents == e['css'].contents[0].contents
    assert e['common_1'].contents[1].output == e['css'].contents[1].output
    assert e['common_1'].contents[1].contents == e['css'].contents[1].contents
    assert len(e['common_1'].urls()) == 1
