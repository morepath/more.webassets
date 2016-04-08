from more.webassets.tweens import InjectorTween, PublisherTween
from morepath.request import Request
from morepath.app import App
from ordered_set import OrderedSet


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


@WebassetsApp.tween_factory()
def webassets_injector_tween(app, handler):
    """ Wraps the response with the injector and the publisher tween.

    See :class:`webassets.tweens.InjectorTween` and
    :class:`webassets.tweens.PublisherTween`.

    """

    env = app.config.webasset_registry.get_environment()

    injector_tween = InjectorTween(env, handler)
    publisher_tween = PublisherTween(env, injector_tween)

    return publisher_tween
