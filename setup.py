from setuptools import find_packages
from setuptools import setup


def parse_requirements(filename):
    with open(filename) as requirements_file:
        return requirements_file.readlines()


def get_long_description():
    with open('README.md') as readme_file:
        return readme_file.read()


setup(
    name='flask-jsonapi',
    version='1.3.1.dev0',
    description='JSONAPI 1.0 implementation for Flask.',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    author='Social WiFi',
    author_email='it@socialwifi.com',
    url='https://github.com/socialwifi/flask-jsonapi',
    packages=find_packages(exclude=['tests']),
    install_requires=parse_requirements('base_requirements.txt'),
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
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ]
)
