import atexit
import inspect
import os.path
import shutil
import tempfile

from dectate import Action
from webassets import Bundle, Environment


class Asset(object):
    """ Represents a registered asset which points to one or more files or
    child-assets.

    """

    __slots__ = ('name', 'assets', 'filters')

    def __init__(self, name, assets, filters):
        self.name = name
        self.assets = assets
        self.filters = filters

    def __eq__(self, other):
        return self.name == self.name \
            and self.assets == self.assets \
            and self.filters == self.filters

    @property
    def is_pure(self):
        """ Returns True if this asset is "pure".

        Pure assets are assets which consist of a single file or a set of
        files which share one common extension.

        """

        if self.is_single_file:
            return True

        extensions = {a.split('.')[-1] for a in self.assets}
        extensions |= {None for a in self.assets if '.' not in a}

        return len(extensions) == 1 and None not in extensions

    @property
    def is_single_file(self):
        """ Returns True if this repesents a single file asset. """
        return len(self.assets) == 1 and '.' in self.assets[0]

    @property
    def path(self):
        """ Returns the path to the single file asset if possible. """
        assert self.is_single_file
        return self.assets[0]

    @property
    def extension(self):
        """ Returns the extension of this asset if it's a pure asset. """
        if self.is_pure:
            return self.assets[0].split('.')[-1]


class WebassetRegistry(object):
    """ A registry managing webasset bundles registered through directives. """

    def __init__(self):

        #: A list of all paths which should be searched for files (in order)
        self.paths = []

        #: The default filters for extensions. Each extension has a webassets
        #: filter string associated with it. (e.g. {'js': 'rjsmin'})
        self.filters = {}

        #: :class:`Asset` objects keyed by their name
        self.assets = {}

        #: The output path for all bundles (a temporary directory by default)
        self.output_path = temporary_directory = tempfile.mkdtemp()
        atexit.register(shutil.rmtree, temporary_directory)

        #: A cache of created bundles
        self.cached_bundles = {}

        #: The url passed to the webasset environment
        self.url = 'assets'

        #: more.webasset only publishes js/css files - other file extensions
        #: need to be compiled into either and mapped accordingly
        self.mapping = {
            'coffee': 'js',
            'dust': 'js',
            'jst': 'js',
            'jsx': 'js',
            'less': 'css',
            'sass': 'css',
            'scss': 'css',
            'ts': 'js',
        }

    def register_path(self, path):
        """ Registers the given path as a path to be searched for files.

        The paths are prepended, so each new path has higher precedence than
        all the already registered paths.

        """
        assert os.path.isabs(path), "absolute paths only"
        self.paths.insert(0, os.path.normpath(path))

    def register_filter(self, name, filter):
        """ Registers a filter, overriding any existing filter of the same
        name.

        """
        self.filters[name] = filter

    def register_asset(self, name, assets, filters=None):
        """ Registers a new asset.

        """

        assert '.' not in name, "asset names may not contain dots ({})".format(
            name
        )

        # keep track of asset bundles
        self.assets[name] = Asset(
            name=name,
            assets=assets,
            filters=filters or self.filters
        )

        # and have one additional asset for each file
        for asset in assets:
            basename = os.path.basename(asset)

            # files are entries with an extension
            if '.' in basename:
                path = os.path.normpath(self.find_file(asset))

                self.assets[basename] = Asset(
                    name=basename,
                    assets=(path, ),
                    filters=filters or self.filters
                )
            else:
                assert asset in self.assets, "unknown asset {}".format(asset)

    def find_file(self, name):
        """ Searches for the given file by name using the current paths. """

        if os.path.isabs(name):
            return name

        searched = set()

        for path in self.paths:
            if path in searched:
                continue

            target = os.path.join(path, name)

            if os.path.isfile(target):
                return target

            searched.add(path)

        raise LookupError("Could not find {} in paths".format(name))

    def merge_filters(self, *filters):
        """ Takes a list of filters and merges them.

        The last filter has the highest precedence.

        """
        result = {}

        for filter in filters:
            if filter:
                result.update(filter)

        return result

    def get_bundles(self, name, filters=None):
        """ Yields all the bundles for the given name (an asset). """

        assert name in self.assets, "unknown asset {}".format(name)
        assert self.output_path, "no webasset_output path set"

        asset = self.assets[name]
        filters = self.merge_filters(self.filters, asset.filters, filters)

        if asset.is_pure:

            if asset.is_single_file:
                files = (asset.path, )
            else:
                files = (
                    a.path for a in (self.assets[a] for a in asset.assets))

            extension = self.mapping.get(asset.extension, asset.extension)
            assert extension in ('js', 'css')

            yield Bundle(
                *files,
                filters=filters.get(asset.extension),
                output='{}.bundle.{}'.format(name, extension)
            )
        else:
            for sub in (self.assets[a] for a in asset.assets):
                for bundle in self.get_bundles(sub.name, filters=filters):
                    yield bundle

    def get_environment(self):
        """ Returns the webassets environment, registering all the bundles. """

        debug = os.environ.get('MORE_WEBASSETS_DEBUG', '').lower().strip() in (
            'true', '1'
        )

        env = Environment(
            directory=self.output_path,
            load_path=self.paths,
            url=self.url,
            debug=debug
        )

        for asset in self.assets:
            bundles = tuple(self.get_bundles(asset))

            js = tuple(b for b in bundles if b.output.endswith('.js'))
            css = tuple(b for b in bundles if b.output.endswith('.css'))

            if js:
                js_bundle = len(js) == 1 and js[0] or Bundle(
                    *js, output='{}.bundle.js'.format(asset)
                )
            else:
                js_bundle = None

            if css:
                css_bundle = len(css) == 1 and css[0] or Bundle(
                    *css, output='{}.bundle.css'.format(asset)
                )
            else:
                css_bundle = None

            if js_bundle and css_bundle:
                js_bundle.next_bundle = asset + '_1'
                env.register(asset, js_bundle)
                env.register(asset + '_1', css_bundle)
            elif js_bundle:
                env.register(asset, js_bundle)
            else:
                env.register(asset, css_bundle)

        return env


class PathMixin(object):

    def absolute_path(self, path):
        if os.path.isabs(path):
            return path
        else:
            return os.path.join(os.path.dirname(self.code_info.path), path)


class WebassetPath(Action, PathMixin):
    """ Registers a path with more.webassets.

    Registered paths are searched for assets registered::

        @App.webasset_path()
        def get_asset_path():
            return 'assets/js'  # relative to the directory of the code file

        @App.webasset('jquery.js')
        def get_jquery_asset():
            yield 'jquery.js'  # expected to be at assets/js/jquery.js

    Registered paths can be accumulated, that is you can't override existing
    paths, you can just add new paths which take precedence
    (think ``PATH=/new/path:$PATH``).

    Therefore paths registered first are searched last and paths registered
    by a parent class are search after paths registered by the child class.

    """

    config = {
        'webasset_registry': WebassetRegistry
    }

    def identifier(self, webasset_registry):
        return object()

    def absolute_path(self, path):
        if os.path.isabs(path):
            return path
        else:
            return os.path.abspath(
                os.path.join(os.path.dirname(self.code_info.path), path)
            )

    def perform(self, obj, webasset_registry):
        path = self.absolute_path(obj())
        assert os.path.isdir(path), "'{}' does not exist".format(path)

        webasset_registry.register_path(self.absolute_path(obj()))


class WebassetOutput(Action, PathMixin):
    """ Sets the output path for all bundles.

    For example::

        @App.webasset_output()
        def get_output_path():
            return 'assets/bundles'

    """

    group_class = WebassetPath

    def identifier(self, webasset_registry):
        return self.__class__

    def perform(self, obj, webasset_registry):
        webasset_registry.output_path = self.absolute_path(obj())


class WebassetFilter(Action):
    """ Registers a default filter for an extension.

    Filters are strings interpreted by `webasset`::

        @App.webasset_filter('js')
        def get_js_filter():
            return 'rjsmin'

        @App.webasset_filter('scss')
        def get_scss_filter():
            return 'pyscss'

    For a list of available filters see
    `<http://webassets.readthedocs.org/en/latest/builtin_filters.html>`_.

    """

    group_class = WebassetPath

    def __init__(self, name):
        self.name = name

    def identifier(self, webasset_registry):
        return self.name

    def perform(self, obj, webasset_registry):
        webasset_registry.register_filter(self.name, obj())


class WebassetMapping(Action):
    """ Maps an extension to either css or js.

    You usually don't have to use this, as more.webassets comes with default
    values. If you do, please open an issue so your mapping may be added
    to more.webassets.

    Example::

        @App.webasset_mapping('jsx')
        def get_jsx_mapping():
            return 'js'

        @App.webasset_mapping('less')
        def get_jsx_mapping():
            return 'css'

    """

    group_class = WebassetPath

    def __init__(self, name):
        self.name = name

    def identifier(self, webasset_registry):
        return self.name

    def perform(self, obj, webasset_registry):
        webasset_registry.mapping[self.name] = obj()


class WebassetUrl(Action):
    """ Defines the url under which the bundles should be served.

    Passed to the webasset environment, this is basically a url path prefix::

        @App.webasset_url()
        def get_webasset_url():
            return 'my-assets'

    Defaults to 'assets'.

    """

    group_class = WebassetPath

    def identifier(self, webasset_registry):
        return self.__class__

    def perform(self, obj, webasset_registry):
        webasset_registry.url = obj()


class Webasset(Action):
    """ Registers an asset which may then be included in the page.

    For example::

        @App.webasset('tooltip')
        def get_tooltip_asset():
            yield 'tooltip.js'
            yield 'tooltip.css'

    Assets may be included by using
    :meth:`more.webassets.core.IncludeRequest.include`::

        @App.view(model=Model)
        def view_model(self, request):
            request.include('tooltip')

    Asset functions must be generators. They may include a mixed set of
    assets. So you can freely mix css, js, less and so on. When you include
    the asset by name those files are automatically put into appropriate
    webasset bundles.

    You may also define a custom filter which only applies to the registered
    assets (they override the default filters registerd by `webasset_filter`)::

        @App.webasset('tooltip', filters={'css': 'cssmin'})
        def get_tooltip_asset():
            yield 'tooltip.js'
            yield 'tooltip.css'

    Assets defined in a parent class may be overridden by using the same
    name, or they may be reused. This means you can have applications which
    define assets for you that you can reuse::

        @BaseApp.webasset('react')
        def get_react_asset():
            yield 'react.js'

        @App.webasset('widget')
        def get_widget_asset():
            yield 'react'
            yield 'widget.jsx'

    Note that webassets may not contain path separators. You're supposed to
    register all paths which should be searched, and then you only work
    with filenames.

    """

    depends = [
        WebassetFilter,
        WebassetMapping,
        WebassetOutput,
        WebassetPath,
        WebassetUrl
    ]
    group_class = WebassetPath

    def __init__(self, name, filters=None):
        self.name = name
        self.filters = filters

    def identifier(self, webasset_registry):
        return self.name

    def perform(self, obj, webasset_registry):
        assert inspect.isgeneratorfunction(obj), "webasset expects a generator"
        webasset_registry.register_asset(
            self.name, tuple(asset for asset in obj()), self.filters
        )
