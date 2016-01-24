More Webassets
==============

Integrates Webassets into Morepath.

`Webassets <https://webassets.readthedocs.org/en/latest/>`_ |
`Morepath <http://morepath.readthedocs.org/en/latest/>`_

This package is somewhat similar to
`more.static <https://github.com/morepath/more.static>`_, which integrates
`bowerstatic <https://bowerstatic.readthedocs.org/en/latest/>`_ into Morepath.
It is currently not really used anywhere, so you should probably stick to
`more.static <https://github.com/morepath/more.static>`_.

Now that you are sufficently discouraged from using more.webassets, these are
the reasons it might be for you:

* You don't have to learn about javascript package managers (i.e. Bower).
* You can have your assets compiled on the fly.
* Your stylesheets are rendered at the top, your scripts at the bottom. No
  configuration necessary.

If you are alreay familiar with webassets: This package might not be as
powerful as you're used to. It currently has little flexibility. It's also
the first time the author uses webassets, so things might be off.

Usage
-----

To get a basic application that serves webassets under `/assets/*`:

.. code-block:: python

    from morepath import reify
    from more.webassets import WebassetsApp
    from webassets import Bundle

    class MyApp(WebassetsApp):

        @reify
        def webassets_bundles(self):
            return {
                'jquery': Bundle(
                    'jquery.js',
                    filters='jsmin',
                    output='bundles/jquery.bundle.js'
                )
            }

    @MyApp.path('')
    class Root(object):
        pass

    @MyApp.html(model=Root):
    def index(self, request):
        request.include('jquery')

        return '<html><head></head><body>hello</body></html>'

This will result in the following html (formatted for readability):

.. code-block:: html

    <html>
        <head></head>
        <body>hello</body>
        <script type="text/javascript" src="./assets/bundles/jquery.bundle.js?1234"></script>
    </html>

For it to work you need an 'assets' folder with a 'jquery.js' file in the
same folder as your python file where 'MyApp' is defined.

Run in Debug Mode
-----------------

To activate the webassets debug mode (which disables bundling), simply add
return the following webassets environment config:

.. code-block:: python

    from morepath import reify
    from more.webassets import WebassetsApp

    class MyApp(WebassetsApp):

        @reify
        def webassets_environment_config(self):
            return {
                'debug': True
            }

Run the Tests
-------------

Install tox and run it::

    pip install tox
    tox

Limit the tests to a specific python version::

    tox -e py27

Conventions
-----------

More Webassets follows PEP8 as close as possible. To test for it run::

    tox -e pep8

More Webassets uses `Semantic Versioning <http://semver.org/>`_

Build Status
------------

.. image:: https://travis-ci.org/morepath/more.webassets.png
  :target: https://travis-ci.org/morepath/more.webassets
  :alt: Build Status

Coverage
--------

.. image:: https://coveralls.io/repos/morepath/more.webassets/badge.png?branch=master
  :target: https://coveralls.io/r/morepath/more.webassets?branch=master
  :alt: Project Coverage

Latests PyPI Release
--------------------
.. image:: https://pypip.in/v/more.webassets/badge.png
  :target: https://crate.io/packages/more.webassets
  :alt: Latest PyPI Release

License
-------
more.webassets is released under the revised BSD license
