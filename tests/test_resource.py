from unittest import mock

import pytest

from flask_jsonapi import exceptions
from flask_jsonapi import resource


class TestResourceList:
    def test_resource_list_get_raise_data_layer_object_not_found_error(self):
        class ExampleResourceList(resource.ResourceList):
            schema = mock.Mock()

            def get_list(self):
                raise resource.DataLayerObjectNotFound('Could not find the object.')

        with pytest.raises(exceptions.ObjectNotFound):
            ExampleResourceList().get()

    def test_resource_list_get_raise_data_layer_error(self):
        class ExampleResourceList(resource.ResourceList):
            schema = mock.Mock()

            def get_list(self):
                raise resource.DataLayerError('Generic data layer error.')

        with pytest.raises(exceptions.JsonApiException):
            ExampleResourceList().get()
