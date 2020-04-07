import os
import subprocess


try:
    from setuptools import setup
    from setuptools import find_packages
    packages = find_packages()
except ImportError:
    from distutils.core import setup
    packages = [x.strip('./').replace('/', '.') for x in os.popen('find -name "__init__.py" | xargs -n1 dirname').read().strip().split('\n')]

setup(
    name='pwnstar',
    python_requires='>=3.7',
    version='0.3.8',
    packages=packages,
    install_requires=[
        'aiohttp'
    ],
    dependency_links=[
    ],
    package_data={
        'pwnstar': ['ws_static/*', 'ws_static/*/*']
    },
    entry_points = {
        'console_scripts': [
            'pwnstar = pwnstar.pwnstar:main',
        ],
    }
)
