0.8.3 (unreleased)
------------------

- Added relationship repositories.


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
