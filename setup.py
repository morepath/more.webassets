# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

name = 'more.webassets'
description = (
    'An opinionated Webassets integration for Morepath.'
)
version = '0.3.3'


def get_long_description():
    import io
    readme = io.open('README.rst', encoding='utf-8').read()
    history = io.open('HISTORY.rst', encoding='utf-8').read()

    # cut the part before the description to avoid repetition on pypi
    readme = readme[readme.index(description) + len(description):]

    return '\n'.join((readme, history))


setup(
    name=name,
    version=version,
    description=description,
    long_description=get_long_description(),
    url='http://github.com/morepath/more.webassets',
    author='Seantis GmbH',
    author_email='info@seantis.ch',
    license='BSD',
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=name.split('.')[:-1],
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=[
        'morepath>=0.16',
        'ordered-set',
        'webassets',
        'webob'
    ],
    extras_require=dict(
        test=[
            'coverage',
            'pytest',
            'webtest',
            'pyscss'
        ],
    ),
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: BSD License',
    ]
)
