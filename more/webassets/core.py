from __future__ import annotations

from typing import TYPE_CHECKING

from ordered_set import OrderedSet

from dectate import directive
from morepath.app import App
from morepath.core import excview_tween_factory
from morepath.request import Request

from . import directives
from .tweens import InjectorTween, PublisherTween

if TYPE_CHECKING:
    from typing_extensions import TypeVar

    from morepath.types import Tween

    _AppT = TypeVar(
        "_AppT", bound="WebassetsApp", default="WebassetsApp", covariant=True
    )
else:
    from typing import TypeVar

    _AppT = TypeVar("_AppT", bound="WebassetsApp", covariant=True)


class IncludeRequest(Request[_AppT]):
    """Adds the ability to include webassets bundles on the request.

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

    included_assets: OrderedSet[str]

    # NOTE: Preserve the signature of the super-class, without duplicating it
    if not TYPE_CHECKING:

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.included_assets = OrderedSet()

    def include(self, resource: str) -> None:
        self.included_assets.add(resource)


class WebassetsApp(App):
    """Defines an app that servers webassets."""

    request_class = IncludeRequest

    webasset_path = directive(directives.WebassetPath)

    webasset_output = directive(directives.WebassetOutput)

    webasset_filter = directive(directives.WebassetFilter)

    webasset_mapping = directive(directives.WebassetMapping)

    webasset_url = directive(directives.WebassetUrl)

    webasset = directive(directives.Webasset)


@WebassetsApp.tween_factory(over=excview_tween_factory)
def webassets_injector_tween(app: WebassetsApp, handler: Tween) -> Tween:
    """Wraps the response with the injector and the publisher tween.

    See :class:`webassets.tweens.InjectorTween` and
    :class:`webassets.tweens.PublisherTween`.

    """

    env = app.config.webasset_registry.get_environment()

    injector_tween = InjectorTween(env, handler)
    publisher_tween = PublisherTween(env, injector_tween)

    return publisher_tween
