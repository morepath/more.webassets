import inspect
import os.path

from dectate import Action
from more.webassets.core import WebassetsApp
from webassets import Bundle, Environment


MISSING = object()


class Asset(object):

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
    def is_single_file(self):
        return len(self.assets) == 1 and '.' in self.assets[0]

    @property
    def path(self):
        assert self.is_single_file
        return self.assets[0]

    @property
    def extension(self):
        if self.is_pure:
            return self.assets[0].split('.')[-1]

    @property
    def is_pure(self):
        if self.is_single_file:
            return True

        extensions = {a.split('.')[-1] for a in self.assets}
        extensions |= {None for a in self.assets if '.' not in a}

        return len(extensions) == 1 and None not in extensions


class WebassetRegistry(object):

    def __init__(self):
        self.paths = []
        self.filters = {}
        self.files = {}
        self.assets = {}
        self.output_path = None
        self.cached_bundles = {}
        self.url = 'assets'
        self.environment_config = {}
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
        assert os.path.isabs(path), "absolute paths only"
        self.paths.insert(0, os.path.normpath(path))

    def register_filter(self, name, filter):
        self.filters[name] = filter

    def register_asset(self, name, assets, filters=None):

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
        result = {}

        for filter in filters:
            if filter:
                result.update(filter)

        return result

    def get_bundles(self, name, filters=None):
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
        env = Environment(
            directory=self.output_path,
            load_path=self.paths,
            url=self.url
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


@WebassetsApp.directive('webasset_path')
class WebassetPath(Action):

    config = {
        'webasset_registry': WebassetRegistry
    }

    def identifier(self, webasset_registry):
        return object()

    def absolute_path(self, path):
        if os.path.isabs(path):
            return path
        else:
            return os.path.join(os.path.dirname(self.code_info.path), path)

    def perform(self, obj, webasset_registry):
        webasset_registry.register_path(self.absolute_path(obj()))


@WebassetsApp.directive('webasset_filter')
class WebassetFilter(Action):

    group_class = WebassetPath

    def __init__(self, name):
        self.name = name

    def identifier(self, webasset_registry):
        return self.name

    def perform(self, obj, webasset_registry):
        webasset_registry.register_filter(self.name, obj())


@WebassetsApp.directive('webasset_output')
class WebassetOutput(Action):

    group_class = WebassetPath

    def identifier(self, webasset_registry):
        return self.__class__

    def perform(self, obj, webasset_registry):
        webasset_registry.output_path = obj()


@WebassetsApp.directive('webasset_mapping')
class WebassetMapping(Action):

    group_class = WebassetPath

    def __init__(self, name):
        self.name = name

    def identifier(self, webasset_registry):
        return self.name

    def perform(self, obj, webasset_registry):
        webasset_registry.mapping[self.name] = obj()


@WebassetsApp.directive('webasset_url')
class WebassetUrl(Action):

    group_class = WebassetPath

    def identifier(self, webasset_registry):
        return self.__class__

    def perform(self, obj, webasset_registry):
        webasset_registry.url = obj()


@WebassetsApp.directive('webasset')
class Webasset(Action):

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
