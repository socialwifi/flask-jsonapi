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
