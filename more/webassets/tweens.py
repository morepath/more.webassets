import os
import time
import webob

from datetime import timedelta
from webob.static import FileApp

# content types and methods that get handled by the injector/publisher
CONTENT_TYPES = {'text/html', 'application/xhtml+xml'}
METHODS = {'GET', 'POST', 'HEAD'}

# arbitrarily define forever as 10 years in the future
FOREVER = timedelta(days=365 * 10).total_seconds()


def is_subpath(directory, path):
    """ Returns true if the given path is inside the given directory. """
    directory = os.path.join(os.path.realpath(directory), '')
    path = os.path.realpath(path)

    # return true, if the common prefix of both is equal to directory
    # e.g. /a/b/c/d.rst and directory is /a/b, the common prefix is /a/b
    return os.path.commonprefix([path, directory]) == directory


class InjectorTween(object):
    """ Injects the webasset urls into the response. """

    def __init__(self, environment, handler):
        self.environment = environment
        self.handler = handler

    def urls_to_inject(self, request, suffix=None):
        for ressource in request.included_assets:
            for url in self.environment[ressource].urls():
                filename, filehash = url.split('?')

                if suffix and not filename.endswith(suffix):
                    continue

                yield '/' + url

    def __call__(self, request):
        response = self.handler(request)

        if request.method not in METHODS:
            return response

        if not response.content_type:  # may be None if the code is != 200
            return response

        if response.content_type.lower() not in CONTENT_TYPES:
            return response

        scripts = '\n'.join(
            '<script type="text/javascript" src="{}"></script>'.format(url)
            for url in self.urls_to_inject(request, '.js')
        )

        stylesheets = '\n'.join(
            '<link rel="stylesheet" type="text/css" href="{}">'.format(url)
            for url in self.urls_to_inject(request, '.css')
        )

        if scripts:
            response.body = response.body.replace(
                b'</html>', scripts.encode('utf-8') + b'</html>'
            )

        if stylesheets:
            response.body = response.body.replace(
                b'</head>', stylesheets.encode('utf-8') + b'</head>'
            )

        return response


class PublisherTween(object):
    """ Returns the webassets if the request begins with the
    :attr:`WebassetsApp.webassets_url`.

    """

    def __init__(self, environment, handler):
        self.environment = environment
        self.handler = handler

    def __call__(self, request):
        publisher_signature = request.path_info_peek()

        if publisher_signature != self.environment.url:
            return self.handler(request)

        subpath = request.path_info.replace(publisher_signature, '').strip('/')

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
