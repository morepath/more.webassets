Changelog
---------

0.3.3 (2016-10-04)
~~~~~~~~~~~~~~~~~~~

0.3.3 (unreleased)
~~~~~~~~~~~~~~~~~~

- Add Python 3.5 and make it the default test environment.

- Update to work with Morepath 0.16.


0.3.2 (2016-04-11)
~~~~~~~~~~~~~~~~~~~

- Ensures that the webasset_path is always an absolute path.
  [href]

0.3.1 (2016-04-11)
~~~~~~~~~~~~~~~~~~~

- Adds a debug environment variable used to activate webasset's debug mode.
  [href]

- Uses a temporary default output directory if none is specified.
  [href]

0.3.0 (2016-04-08)
~~~~~~~~~~~~~~~~~~~

- *Breaking Changes* - This release changes everything!

  Assets are no longer registerd through special methods on the application.
  Instead proper Morepath directives are used. This enables better re-use
  of assets, less verbosity and proper support of inheritance (you can now
  have applications which define assets and child-applications which use
  those assets).

  Have a look at the `readme <https://github.com/morepath/more.webassets>`_ and
  at `the comments in the directives file <https://github.com/morepath/more.webassets/blob/master/more/webassets/directives.py>`_, to get an idea about what has changed.

  Don't hesitate to open an issue if you need help migrating your existing
  setup.

0.2.0 (2016-04-06)
~~~~~~~~~~~~~~~~~~~

- Adds compatibility with morepath 0.13.
  [href]

0.1.1 (2016-01-24)
~~~~~~~~~~~~~~~~~~~

- Disables webassets url caching if debug mode is active.
  [href]

0.1.0 (2016-01-24)
~~~~~~~~~~~~~~~~~~~

- Support webassets debug mode (before it would trigger an exception).
  [href]

0.0.3 (2015-08-07)
~~~~~~~~~~~~~~~~~~~

- Cache the resource urls for increased speed. Note that with this change a
  reload of the application is necessary to get the updated javascript files.

  If this is an issue for you, speak up and we might add a debug flag.
  [href]

0.0.2 (2015-05-18)
~~~~~~~~~~~~~~~~~~~

- Adds more checks to ensure we never serve anything outside the assets
  directory.
  [href]

0.0.1 (2015-04-29)
~~~~~~~~~~~~~~~~~~~

- Initial Release [href]
