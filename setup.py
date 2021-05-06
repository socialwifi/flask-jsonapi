import pathlib

import pkg_resources

from setuptools import find_packages
from setuptools import setup

with pathlib.Path('base_requirements.txt').open() as requirements_txt:
    install_requires = [
        str(requirement) for requirement in pkg_resources.parse_requirements(requirements_txt)
    ]

setup(
    name='flask-jsonapi',
    version='0.20.0',
    description='JSONAPI 1.0 implementation for Flask.',
    author='Social WiFi',
    author_email='it@socialwifi.com',
    url='https://github.com/socialwifi/flask-jsonapi',
    packages=find_packages(exclude=['tests']),
    install_requires=install_requires,
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    extras_require={
        'sqlalchemy': ['sqlalchemy']
    },
    license='BSD',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ]
)
