"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path


def read(rel_path):
    here = path.abspath(path.dirname(__file__))
    with open(filename=path.join(here, rel_path), mode='r') as fp:
        return fp.read()


def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


def get_description(rel_path):
    here = path.abspath(path.dirname(__file__))
    # Get the long description from the README file
    with open(path.join(here, rel_path), encoding='utf-8') as f:
        return f.read()

setup(
    name='routing',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=get_version("routing/__init__.py"),

    description='Routing Service: service to find where seismological data can be accessed',
    long_description=get_description('README.rst'),

    # The project's main homepage.
    url='https://github.com/EIDA/routing',

    # Author details
    author='Javier Quinteros',
    author_email='javier@gfz.de',

    # Choose your license
    license='GPLv3',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        "Framework :: FastAPI",
        "Framework :: Pydantic :: 2",
        'Intended Audience :: Science/Research',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware',
        'Topic :: Scientific/Engineering'
    ],

    # What does your project relate to?
    keywords='seismology DAS waveforms fdsnws',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),

    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
    # py_modules=["whatever"],
    provides=["routing"],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=['fastapi', 'uvicorn', 'pydantic>=2', 'sphinx'],

    python_requires='>=3',
    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    # extras_require={
    #     'dev': ['check-manifest'],
    #     'test': ['coverage'],
    # },

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    # package_data={},
    include_package_data=True,
    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    # data_files=[(path.join('/', path.expanduser('~'), '.owndc'), ['owndc.cfg']),
    #             (path.join('/', path.expanduser('~'), '.owndc', 'data'), ['data/owndc-routes.xml']),
    #             (path.join('/', path.expanduser('~'), '.owndc', 'data'), ['data/masterTable.xml'])
    #             ],

    package_data={'routing': ['data/*.json', 'data/*.wadl', 'data/*.xml', 'data/*.html']},

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points='''
        [console_scripts]
        routingsvc=routing.routing:main
        routing-update=routing.routingupdate:main
    '''
)
