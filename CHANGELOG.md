## 1.5.0 (unreleased)
---------------------

- Add `flask_jsonapi.ViewSet`, `DetailView` and `ListView`: a layered way to declare a resource. A ViewSet declares
  `allowed_actions`, `guards`, `object_permissions`, `middlewares` and one `data_service`, which run in a fixed
  order: allowed actions and guards before the request body is parsed, then object permissions, middlewares and
  the data service. `flask_jsonapi.guards` and `flask_jsonapi.middlewares` (`Middleware`, `build_pipeline`,
  `CheckRequiredListFilters`) are new.
- Add `flask_jsonapi.permissions.ObjectPermissions` and `CheckObjectPermission` for the `object_permissions` slot.
  `CheckObjectPermission` plugs an existing `PermissionChecker` into a ViewSet. Its `apply_permission_filter`
  returns filters that restrict a list to the objects the client may list, and may raise `PermissionException`
  (403) when the client's own filters ask for objects it may not list. `check_list_permission` runs on the listed
  objects as a safety net: if it drops any, a warning is logged and the total is left out of the response.
- Add `flask_jsonapi.data_services`: HTTP-agnostic data services that raise their own exceptions
  (`ResourceNotFound`, `PermissionDenied`, `InvalidData`, `Conflict`, ...), which a view translates to JSON:API
  errors. Data services, middlewares and object permissions name their methods after the actions: `create`,
  `read`, `list`, `update` and `destroy`. It includes a new `SqlAlchemyModelRepository` and
  `LegacyRepositoryAdapter`, which lets a new ViewSet use a legacy repository (`PATCH` then answers 200 with a body
  instead of 204).
- Add `flask_jsonapi.data_services.ListResult(items, total)`, which `list` returns: the items, and the number of
  objects matching the filters before pagination, or `None`. A data service sets the total when the request asks
  for a page. `ListView` calls `list` once per request and builds the pagination links from the total. Without a
  total, `last` is `null` and `next` is present only for a full page. `SqlAlchemyModelRepository.list` counts and
  slices one filtered query. `LegacyRepositoryAdapter.list` calls `get_count` only when the request asks for a page.
- Add `flask_jsonapi.resources.ListResourceBase`, the base class of `ResourceList` and `ListView`, and
  `SizeNumberPagination.get_links_without_total`. A custom pagination class used by `ListView` must implement
  `get_links` and `get_links_without_total`.
- Add `Actions.list`. `Actions.read_many` stays as an alias with the same value.
- Deprecate `ResourceRepositoryViewSet`, `ResourceRepositoryDetailView`, `ResourceRepositoryListView`,
  `ProtectedViewSet`, `ProtectedDetailView`, `ProtectedListView`, the `AllowedActions*` mixins, `ResourceRepository`
  and the legacy `SqlAlchemyModelRepository` (documented only, there are no runtime warnings). See the migration guide.
- Every error from a view is now a JSON:API error document, for legacy views too. Unexpected exceptions are logged and
  rendered as a generic 500 without internal details, and `flask.abort()` keeps its status, title and headers (for
  example `WWW-Authenticate`). An `abort()` carrying an explicit response returns that response unchanged.
- Flask app error handlers (`@app.errorhandler`) no longer run for exceptions raised inside flask-jsonapi views:
  those become JSON:API errors, unexpected ones a generic 500. In testing mode such exceptions no longer reach the
  test client either.
- Errors while dumping a GET response (`AttributeError`, `KeyError`, `ValueError` from a schema) are a generic 500
  without details instead of a 500 whose `detail` is the exception message.
- `HEAD` is served by the `GET` handler instead of failing with a 500.
- `PATCH` with a wrong resource `type` answers 409 Conflict instead of 500.
- JSON:API exception classes accept keyword arguments (`status`, `title`, `detail`, `source`). The old positional
  forms still work. New exceptions: `Unauthorized`, `UnprocessableEntity` and `ServiceUnavailable`.
- `str(exc)` of a JSON:API exception is now its `detail`. Without a `source` argument, `ForbiddenError(...).source`
  and `MethodNotAllowed(...).source` are now `None` instead of `{}`; `to_dict()` is unaffected.
- Empty `detail` and `source` are omitted from error objects. Tests that compare a whole error body to one with
  `'source': {}` need updating.


## 1.4.2 (unreleased)
---------------------

- Fix duplicated Content-Type header in JSON:API responses.
- `BaseJsonApiResponse.base_header` was replaced by `content_type`. A Content-Type header supplied by the
  caller is now overridden by the JSON:API one.
- Return 409 Conflict when a PATCH body id does not match the URL. This also applies to a body id that
  differs from the URL id only in letter case (for example an uppercase UUID): legacy repository views
  used to overwrite the body id with the URL id and succeed, so clients sending such ids now get 409.


## 1.4.1 (2026-02-02)
---------------------

- Lock marshmallow version below 4.0.


## 1.4.0 (2026-02-02)
------------------

- Support filtering for models using inheritance.
- Raise exceptions when filters are not matched.
- Fix tests.
- Remove "six" usage.


1.3.0 (2022-03-17)
------------------

- Add allowed_actions for ViewSet and View.
- Allow overriding resource action methods in protected views.


1.2.0 (2021-11-22)
------------------

- Parametrize session commits.


1.1.0 (2021-06-17)
------------------

- Add support for custom pagination links via X-Original-Path header.


1.0.0 (2021-06-02)
------------------

- Remove old nested repositories support


0.11.0 (2021-05-07)
-------------------

- Migrate to Marshmallow 3.X


0.10.3 (2019-09-17)
-------------------

- Fixed package description.


0.10.2 (2019-09-17)
-------------------

- Fixed marshmallow error reporting for list/detail requests.


0.10.1 (2019-08-27)
-------------------

- Freeze marshmallow version below 3.0.0.


0.10.0 (2019-03-15)
-------------------

- Add interfaces for permission checking.
- Drop python 3.5 and 3.6 support. From now only 3.7 is supported.


0.9.2 (2018-11-15)
------------------

- Fix in operator bug.


0.9.1 (2018-08-23)
------------------

- Add sorting.
- Fix bug empty filter value.


0.8.3 (2018-08-17)
------------------

- Support filtering.


0.8.2 (2018-07-26)
------------------

- Support Python 3.7.0.


0.8.1 (2018-07-03)
------------------

- Added sparse fields.


0.8.0 (2018-06-11)
------------------

- Added pagination support.


0.7.0 (2017-11-20)
------------------

- Added SQLAlchemy repository implementation.


0.6.0 (2017-11-13)
------------------

- Refactored nested configuration.
- Create nested objects in transaction (if supported by the reposistory).
- Made overriding view classes in viewsets easier.


0.5.1 (2017-11-02)
------------------

- Fixed getting nested resources.


0.5.0 (2017-10-30)
------------------

- Added creating many objects in one request.


0.4.0 (2017-10-13)
------------------

- Added inclusion of related resources. ([specification](http://jsonapi.org/format/#fetching-includes))


0.3.0 (2017-09-25)
------------------

- Added `flask_jsonapi.decorators.selective_decorator` to decorate only desired HTTP methods. 


0.2.1 (2017-06-28)
------------------

- Fix returning status code on list get.


0.2.0 (2017-06-07)
------------------

- Dropped python 3.4 support
- Added ResourceRepositoryViewSet


0.1.0 (2017-05-31)
------------------

- Initial release
