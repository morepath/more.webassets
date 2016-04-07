import inspect
import os.path

from collections import namedtuple
from dectate import Action
from more.webassets.core import WebassetsApp


MISSING = object()
Asset = namedtuple('Asset', ['name', 'assets', 'filters'])


class WebassetRegistry(object):

    def __init__(self):
        self.paths = []
        self.filters = {}
        self.files = {}
        self.assets = {}
        self.output_path = None

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
            name = os.path.basename(asset)

            # files are entries with an extension
            if '.' in name:
                path = os.path.normpath(self.find_file(asset))

                self.assets[name] = Asset(
                    name=name,
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


@WebassetsApp.directive('webasset_path')
class WebassetPath(Action):

    config = {
        'webasset_registry': WebassetRegistry
    }

    def __init__(self):
        pass

    def identifier(self, webasset_registry):
        return object()

    def absolute_path(self, path):
        return os.path.join(os.path.dirname(self.code_info.path), path)

    def perform(self, obj, webasset_registry):
        assert inspect.isgeneratorfunction(obj),\
            "webasset_path expects a generator"

        for path in (self.absolute_path(p) for p in obj()):
            webasset_registry.register_path(path)


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

    def __init__(self):
        pass

    def identifier(self, webasset_registry):
        return 'webasset_output'

    def perform(self, obj, webasset_registry):
        webasset_registry.output_path = obj()


@WebassetsApp.directive('webasset')
class Webasset(Action):

    dependes = [WebassetPath, WebassetFilter, WebassetOutput]
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
