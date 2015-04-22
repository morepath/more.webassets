import more.webassets
import morepath
import os
import pytest

from datetime import datetime
from more.webassets import WebassetsApp
from more.webassets.tweens import is_subpath
from webassets import Bundle
from webtest import TestApp as Client


def prepare_fixtures(directory):
    os.mkdir(os.path.join(directory, 'common'))
    os.mkdir(os.path.join(directory, 'bundles'))
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

    with open(os.path.join(directory, 'common', 'extra.js'), 'w') as f:
        f.write("""
            $(document).ready(function(){});
        """)


def spawn_test_app(tempdir):
    prepare_fixtures(tempdir)

    config = morepath.setup()
    config.scan(more.webassets)

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

    class TestApp(WebassetsApp):
        testing_config = config

        @morepath.reify
        def webassets_path(self):
            return tempdir

        @morepath.reify
        def webassets_bundles(self):
            return {
                'common': Bundle(
                    'common/jquery.js',
                    'common/underscore.js',
                    filters='rjsmin',
                    output='bundles/common.bundle.js'
                ),
                'theme': Bundle(
                    'theme/main.scss',
                    filters='pyscss',
                    output='bundles/theme.bundle.css'
                ),
                'extra': Bundle(
                    'common/extra.js',
                    filters='rjsmin',
                    output='bundles/extra.bundle.js'
                )
            }

    @TestApp.path('')
    class Root(object):
        pass

    @TestApp.html(model=Root)
    def index(self, request):
        bundle = request.params.get('bundle')

        if bundle:
            request.include(bundle)

        return html

    @TestApp.view(model=Root, name='plain', render=render_plain)
    def plain(self, request):
        request.include('common')
        return html

    @TestApp.html(model=Root, name='put', request_method='PUT')
    def put(self, request):
        request.include('common')
        return html

    @TestApp.html(model=Root, name='alljs')
    def alljs(self, request):
        request.include('common')
        request.include('extra')
        return html

    config.commit()

    return TestApp()


def test_inject_webassets(tempdir):
    client = Client(spawn_test_app(tempdir))

    assert '<head></head>' in client.get('/').text

    with pytest.raises(KeyError):
        assert '<head></head>' in client.get('?bundle=inexistant').text

    # the version of these assets stays the same because it's basically the
    # md5 hash of the javascript files included
    injected_html = (
        '<script type="text/javascript" '
        'src="/assets/bundles/common.bundle.js?ddc71aa3"></script></html>')

    assert injected_html in client.get('?bundle=common').text

    injected_html = (
        '<link rel="stylesheet" type="text/css" '
        'href="/assets/bundles/theme.bundle.css?32fda411"></head>')

    assert injected_html in client.get('?bundle=theme').text

    page = client.get('/alljs').text
    assert page.find('common.bundle.js') < page.find('extra.bundle.js')


def test_publish_webassets(tempdir):
    client = Client(spawn_test_app(tempdir))

    url = '/assets/bundles/common.bundle.js?ddc71aa3'

    # before the urls() have not been called by the injector, the bundles
    # won't have been created
    assert client.get(url, expect_errors=True).status_code == 404

    client.get('?bundle=common')

    assert client.get(url).text == 'var $=function(){};var _=function(){};'
    assert client.get(url).expires.year == datetime.utcnow().year + 10
    assert client.get(url).content_type == 'text/javascript'

    # do the same for css
    url = '/assets/bundles/theme.bundle.css?32fda411'

    assert client.get(url, expect_errors=True).status_code == 404

    client.get('?bundle=theme')

    assert client.get(url).text == 'body a {\n  color: blue; }\n'
    assert client.get(url).expires.year == datetime.utcnow().year + 10
    assert client.get(url).content_type == 'text/css'


def test_webassets_defaults():
    config = morepath.setup()
    config.scan(more.webassets)

    class TestApp(WebassetsApp):
        testing_config = config

    config.commit()

    app = TestApp()

    # by default the webassets path is the 'assets' directory in the same
    # directory as the definition of the application class
    assert app.webassets_path.endswith('webassets/tests/assets')
    assert app.webassets_bundles == {}


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
