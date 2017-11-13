from pip.req import parse_requirements
from setuptools import setup
from setuptools import find_packages


setup(
    name='flask-jsonapi',
    version='0.6.0',
    description='JSONAPI 1.0 implementation for Flask.',
    author='SocialWifi',
    author_email='it@socialwifi.com',
    url='https://github.com/socialwifi/flask_jsonapi',
    packages=find_packages(exclude=['tests']),
    install_requires=[str(ir.req) for ir in parse_requirements('base_requirements.txt', session=False)],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    license='BSD',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ]
)