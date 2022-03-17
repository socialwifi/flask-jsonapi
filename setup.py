import pathlib

import pkg_resources

from setuptools import find_packages
from setuptools import setup

with pathlib.Path('base_requirements.txt').open() as requirements_txt:
    install_requires = [
        str(requirement) for requirement in pkg_resources.parse_requirements(requirements_txt)
    ]


def get_long_description():
    with open('README.md') as readme_file:
        return readme_file.read()


setup(
    name='flask-jsonapi',
    version='1.3.0',
    description='JSONAPI 1.0 implementation for Flask.',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    author='Social WiFi',
    author_email='it@socialwifi.com',
    url='https://github.com/socialwifi/flask-jsonapi',
    packages=find_packages(exclude=['tests']),
    install_requires=install_requires,
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    extras_require={
        'sqlalchemy': ['sqlalchemy', 'sqlalchemy_utils']
    },
    license='BSD',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ]
)
