import inspect
import os

from more.webassets.tweens import InjectorTween, PublisherTween
from morepath.request import Request
from morepath.reify import reify
from morepath.app import App
from ordered_set import OrderedSet
from webassets import Environment


class IncludeRequest(Request):
    """ Adds the ability to include webassets bundles on the request.

    If the bundle does not exist, a KeyError will be raised during the
    rendering of the response, after the view has returned.

    Including a bundle multiple times will have the same result as
    including it once.

    The bundles are rendered in the order in which they were included. Bundles
    that are included first, are also rendered first.

    For example:

        @App.html(model=Model)
        def view(self, request):
            request.include('jquery')  # includes the jquery bundle

    """

    def __init__(self, *args, **kwargs):
        super(IncludeRequest, self).__init__(*args, **kwargs)
        self.included_assets = OrderedSet()

    def include(self, resource):
        self.included_assets.add(resource)


class WebassetsApp(App):
    """ Defines an app that servers webassets. """

    request_class = IncludeRequest

    @reify
    def webassets_url(self):
        """ The url or signature under which the assets will be served.

        Note that if this url conflicts with anything in your Morepath app,
        you won't know about it as there are no checks.

        So if you're not sure what kind of paths you are going to be serving,
        just use a random url that stays the same between app restarts.

        """
        return 'assets'

    @reify
    def webassets_path(self):
        """ The path inside which the assets are stored.

        WARNING: files inside that path are available to the public once you
        serve your web application!

        By default, the 'assets' folder in the same folder as the application
        is used. So if this is your folder structure::

            /app/main.py <- where your application is

        Then this is where your assets will be by default::

            /app/assets/

        Change this path by overriding this property in your subclass.
        """

        app_path = os.path.dirname(inspect.getfile(self.__class__))
        return os.path.join(app_path, 'assets')

    @reify
    def webassets_bundles(self):
        """ The webasset bundles that you serve.

        This should be a dictionary with the key being the id of the bundle
        and the value being a webassets.Bundle instance.

        For example::

            @reify
            def webassets_bundles(self):
                return {
                    'common': Bundle(
                        'common/jquery.js',
                        'common/underscore.js',
                        filters='jsmin',
                        output='bundles/common.bundle.js'
                    )
                }

        You would include this bundle like this::

            request.include('common')

        See also: `<http://webassets.readthedocs.org/en/latest/bundles.html>`_

        """

        return {}

    @reify
    def webassets_environment(self):
        """ Returns the webassets.Environment instance.

        See: `<http://webassets.readthedocs.org/en/latest/environment.html`_

        """
        env = Environment(
            self.webassets_path, self.webassets_url,
            **self.webassets_environment_config)

        for key, bundle in self.webassets_bundles.items():
            env.register(key, bundle)

        return env

    @reify
    def webassets_environment_config(self):
        """ Returns custom configuration options used to build the
        webassets environment.

        See `<http://webassets.readthedocs.org/en/latest/environment.html\
        #configuration>`_
        """
        return {}


@WebassetsApp.tween_factory()
def webassets_injector_tween(app, handler):
    """ Wraps the response with the injector and the publisher tween.

    See :class:`webassets.tweens.InjectorTween` and
    :class:`webassets.tweens.PublisherTween`.

    """

    env = app.webassets_environment

    injector_tween = InjectorTween(env, handler)
    publisher_tween = PublisherTween(env, injector_tween)

    return publisher_tween
