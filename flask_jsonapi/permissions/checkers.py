import abc
import http
import typing

from flask_jsonapi import exceptions
from flask_jsonapi.permissions import actions


class PermissionException(exceptions.JsonApiException):
    status = http.HTTPStatus.FORBIDDEN.value
    title = http.HTTPStatus.FORBIDDEN.phrase

    def __init__(self, source=None, detail=None, *args, title=None, status=None, **kwargs):
        super().__init__(source, detail, *args, title=title, status=status, **kwargs)


Resource = typing.TypeVar('Resource')


class PermissionChecker(abc.ABC):
    @abc.abstractmethod
    def check_read_permission(self, *, resource: Resource) -> Resource:
        """
        :param resource: resource for which we want to check permissions
        :return: resource if user has permission, exception in other case
        """
        pass

    @abc.abstractmethod
    def check_destroy_permission(self, *, resource: Resource) -> Resource:
        """
        :param resource: resource for which we want to check permissions
        :return: resource if user has permission, exception in other case
        """
        pass

    @abc.abstractmethod
    def check_update_permission(self, *, resource: Resource, data: dict) -> typing.Tuple[Resource, dict]:
        """
        :param resource: resource for which we want to check permissions
        :param data: new data
        :return: new data if user has permission, exception in other case
        """
        pass

    def check_list_permission(self, *, resources: typing.List[Resource]) -> typing.List[Resource]:
        """
        :param resources: resources list for which we want to check permissions
        :return: filtered resources list
        """
        result = []
        for resource in resources:
            try:
                result.append(self.check_read_permission(resource=resource))
            except PermissionException:
                pass
        return result

    @abc.abstractmethod
    def check_create_permission(self, *, data: dict) -> dict:
        """
        :param data: data for which we want to check permissions
        :return: data if user has permission, exception in other case
        """
        pass


class ObjectLevelPermissionChecker(PermissionChecker):
    class ObjectIdNotFoundInData(Exception):
        pass

    @property
    @abc.abstractmethod
    def object_id_attribute(self) -> str:
        pass

    def check_create_permission(self, *, data: dict) -> dict:
        return self._check_data_permission(data=data, action=actions.CREATE_ACTION)

    def check_read_permission(self, *, resource: Resource) -> Resource:
        return self._check_resource_permission(resource=resource, action=actions.READ_ACTION)

    def check_update_permission(self, *, resource: Resource, data: dict) -> typing.Tuple[Resource, dict]:
        self._check_resource_permission(resource=resource, action=actions.UPDATE_ACTION)
        try:
            self._check_data_permission(data=data, action=actions.UPDATE_ACTION)
        except self.ObjectIdNotFoundInData:
            pass
        return resource, data

    def check_destroy_permission(self, *, resource) -> Resource:
        return self._check_resource_permission(resource=resource, action=actions.DESTROY_ACTION)

    def _check_resource_permission(self, *, resource: Resource, action: str) -> Resource:
        object_id = self.get_object_id_from_resource(resource)
        self.check_or_raise(object_id=object_id, action=action)
        return resource

    def _check_data_permission(self, *, data: dict, action: str):
        object_id = self.get_object_id_from_data(data)
        self.check_or_raise(object_id=object_id, action=action)
        return data

    def get_object_id_from_resource(self, resource: Resource):
        return getattr(resource, self.object_id_attribute)

    def get_object_id_from_data(self, data: dict):
        try:
            return data[self.object_id_attribute]
        except KeyError:
            raise self.ObjectIdNotFoundInData

    def check_or_raise(self, *, object_id, action: str):
        has_permission = self.has_permission(
            object_id=object_id,
            action=action,
        )
        if not has_permission:
            raise PermissionException

    @abc.abstractmethod
    def has_permission(self, object_id, action) -> bool:
        pass
