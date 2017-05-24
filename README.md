# flask-jsonapi
[![Build Status](https://travis-ci.org/socialwifi/flask-jsonapi.svg?branch=master)](https://travis-ci.org/socialwifi/flask-jsonapi)
[![Latest Version](https://img.shields.io/pypi/v/flask-jsonapi.svg)](https://github.com/socialwifi/flask-jsonapi/blob/master/CHANGELOG.md)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/flask-jsonapi.svg)](https://pypi.python.org/pypi/flask-jsonapi/)
[![Wheel Status](https://img.shields.io/pypi/wheel/flask-jsonapi.svg)](https://pypi.python.org/pypi/flask-jsonapi/)
[![License](https://img.shields.io/pypi/l/flask-jsonapi.svg)](https://github.com/socialwifi/flask-jsonapi/blob/master/LICENSE)

JSONAPI 1.0 server implementation for Flask.

## Running tests

```
virtualenv -p python3.6 ~/flask-jsonapi-virtualenv
. ~/flask-jsonapi-virtualenv/bin/activate
pip install -r base_requirements.txt
pip install -U pytest==3.0.5
pytest
```

## Credits

Some parts of this project were written based on [Flask-REST-JSONAPI](https://github.com/miLibris/flask-rest-jsonapi).
