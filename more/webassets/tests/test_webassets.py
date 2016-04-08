import more.webassets
import morepath
import os
import pytest

from datetime import datetime
from more.webassets import WebassetsApp
from more.webassets.tweens import is_subpath, has_insecure_path_element
from webtest import TestApp as Client


def prepare_fixtures(directory):
    os.mkdir(os.path.join(directory, 'common'))
    os.mkdir(os.path.join(directory, 'output'))
    os.mkdir(os.path.join(directory, 'theme'))

    # if those javascripts are changed, the tests below need to be updated
    # with the correct md5 hashes
    with open(os.path.join(directory, 'common', 'jquery.js'), 'w') as f:
        f.write("""
            /* fake jquery */
            var $ = function(){};
        """)

    with open(os.path.join(directory, 'common', 'underscore.js'), 'w') as f:
        f.write("""
            /* fake underscore */
            var _ = function(){};
        """)

    with open(os.path.join(directory, 'theme', 'main.scss'), 'w') as f:
        f.write("""
            body {
                a {
                    color: blue;
                }
            }
        """)

    with open(os.path.join(directory, 'theme', 'other.css'), 'w') as f:
        f.write("""
            h1 {
                font-size: 2rem;
            }
        """)

    with open(os.path.join(directory, 'common', 'extra.js'), 'w') as f:
        f.write("""
            $(document).ready(function(){});
        """)


def spawn_test_app(tempdir):
    prepare_fixtures(tempdir)

    html = """
        <html>
            <head></head>
            <body>
                <p>Bar</p>
            </body>
        </html>
    """

    def render_plain(content, request):
        response = morepath.Response(content)
        response.content_type = 'text/plain'
        return response

    class App(WebassetsApp):
        pass

    @App.webasset_path()
    def get_default_assets_path():
        return os.path.join(tempdir, 'common')

    @App.webasset_path()
    def get_theme_assets_path():
        return os.path.join(tempdir, 'theme')

    @App.webasset_output()
    def get_output_path():
        return os.path.join(tempdir, 'output')

    @App.webasset_filter('js')
    def get_js_filter():
        return 'rjsmin'

    @App.webasset_filter('scss')
    def get_scss_filter():
        return 'pyscss'

    @App.webasset(name='common')
    def get_common_assets():
        yield 'jquery.js'
        yield 'underscore.js'

    @App.webasset(name='extra')
    def get_extra_asset():
        yield 'extra.js'

    @App.webasset(name='theme')
    def get_theme_asset():
        yield 'main.scss'

    @App.path('')
    class Root(object):
        pass

    @App.html(model=Root)
    def index(self, request):
        bundle = request.params.get('bundle')

        if bundle:
            request.include(bundle)

        return html

    @App.view(model=Root, name='plain', render=render_plain)
    def plain(self, request):
        request.include('common')
        return html

    @App.html(model=Root, name='put', request_method='PUT')
    def put(self, request):
        request.include('common')
        return html

    @App.html(model=Root, name='alljs')
    def alljs(self, request):
        request.include('common')
        request.include('extra')
        return html

    morepath.scan(more.webassets)
    morepath.commit(App)

    return App()


def test_inject_webassets(tempdir):
    client = Client(spawn_test_app(tempdir))

    assert '<head></head>' in client.get('/').text

    with pytest.raises(KeyError):
        assert '<head></head>' in client.get('?bundle=inexistant').text

    # the version of these assets stays the same because it's basically the
    # md5 hash of the javascript files included
    injected_html = (
        '<script type="text/javascript" '
        'src="/assets/common.bundle.js?ddc71aa3"></script></html>')

    assert injected_html in client.get('?bundle=common').text

    injected_html = (
        '<link rel="stylesheet" type="text/css" '
        'href="/assets/theme.bundle.css?32fda411"></head>')

    assert injected_html in client.get('?bundle=theme').text

    page = client.get('/alljs').text
    assert page.find('common.bundle.js') < page.find('extra.bundle.js')


def test_publish_webassets(tempdir):
    client = Client(spawn_test_app(tempdir))

    url = '/assets/common.bundle.js?ddc71aa3'

    # before the urls() have not been called by the injector, the bundles
    # won't have been created
    assert client.get(url, expect_errors=True).status_code == 404

    client.get('?bundle=common')

    assert client.get(url).text == 'var $=function(){};var _=function(){};'
    assert client.get(url).expires.year == datetime.utcnow().year + 10
    assert client.get(url).content_type == 'text/javascript'

    # do the same for css
    url = '/assets/theme.bundle.css?32fda411'

    assert client.get(url, expect_errors=True).status_code == 404

    client.get('?bundle=theme')

    assert client.get(url).text == 'body a {\n  color: blue; }\n'
    assert client.get(url).expires.year == datetime.utcnow().year + 10
    assert client.get(url).content_type == 'text/css'


def test_webassets_unhandled_content_type(tempdir):
    client = Client(spawn_test_app(tempdir))

    assert '<head></head>' in client.get('/plain').text


def test_webassets_unhandled_request_method(tempdir):
    client = Client(spawn_test_app(tempdir))

    assert '<head></head>' in client.put('/put').text


def test_is_subpath(tempdir):
    assert is_subpath('/', '/test')
    assert is_subpath('/asdf', '/asdf/asdf')
    assert not is_subpath('/asdf/', '/asdf')
    assert not is_subpath('/a', '/b')
    assert not is_subpath('/a', '/a/../b')


def test_insecure_path_element():
    assert has_insecure_path_element('../test.txt')
    assert has_insecure_path_element('./test.txt')
    assert has_insecure_path_element('/test.txt')
    assert not has_insecure_path_element('test.txt')
    assert not has_insecure_path_element('asdf/asdf/test.txt')
