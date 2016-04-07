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
        yield './fixtures'

    @App.webasset_path()
    def get_overlapping_path():
        yield os.path.join(current_path, './fixtures')

    @App.webasset_path()
    def get_multiple_paths():
        yield '.'
        yield '..'

    morepath.commit(App)

    app = App()

    assert app.config.webasset_registry.paths == [
        os.path.normpath(os.path.join(current_path, '..')),
        os.path.normpath(os.path.join(current_path, '.')),
        os.path.normpath(os.path.join(current_path, 'fixtures')),
        os.path.normpath(os.path.join(current_path, 'fixtures')),
    ]


def test_webasset_path_inheritance(current_path):

    class A(WebassetsApp):
        pass

    @A.webasset_path()
    def get_path_a():
        yield 'A'

    class B(WebassetsApp):
        pass

    @B.webasset_path()
    def get_path_b():
        yield 'B'

    class C(B, A):
        pass

    @C.webasset_path()
    def get_path_c():
        yield 'C'

    class D(A, B):
        pass

    @D.webasset_path()
    def get_path_c_2():
        yield 'C'

    # the order of A and B is defined by the order they are scanned with
    morepath.commit(A, B, C, D)

    assert C().config.webasset_registry.paths == [
        os.path.normpath(os.path.join(current_path, 'C')),
        os.path.normpath(os.path.join(current_path, 'B')),
        os.path.normpath(os.path.join(current_path, 'A')),
    ]

    assert D().config.webasset_registry.paths == [
        os.path.normpath(os.path.join(current_path, 'C')),
        os.path.normpath(os.path.join(current_path, 'B')),
        os.path.normpath(os.path.join(current_path, 'A')),
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
        yield fixtures_path

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
