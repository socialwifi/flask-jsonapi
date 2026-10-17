Views
=====

.. versionadded:: 1.5.0

:class:`flask_jsonapi.DetailView` and :class:`flask_jsonapi.ListView` are the views a
:doc:`ViewSet <view_sets>` registers. You normally do not instantiate them: ``ViewSet.as_detail_view`` and
``ViewSet.as_list_view`` build them from the ViewSet's attributes.

Both views are Flask class based views. ``DetailView`` is built on ``ResourceDetail``, and ``ListView`` on
``ListResourceBase``. These bases parse the query
string (``include``, ``fields``, ``sort``, ``page``, filters), dump the response and check the ``Content-Type`` and
``Accept`` headers. The views add a fixed way to reach the data: allowed actions, then guards, then the pipeline of
object permissions, middlewares and data service.

Arguments
---------

Both views take these keyword arguments, which the ViewSet passes from its attributes:

* ``schema``: the schema class.
* ``data_service``: the data service, innermost layer of the pipeline.
* ``allowed_actions``: the set of served actions.
* ``guards``: the guards, checked in order.
* ``object_permissions``: the object permission layer or ``None``. The view places it outermost in the pipeline.
* ``middlewares``: the middlewares, outermost first. The view wraps them around the data service.

``ListView`` also takes ``filter_schema``.

To use a view subclass of your own, set ``detail_view_class`` or ``list_view_class`` on the ViewSet. If the
subclass takes extra keyword arguments, add them in ``ViewSet.get_views_kwargs``. Those keyword arguments reach
both the detail and the list view, so both view classes must accept them: the base views reject unknown ones.

What each method does
---------------------

``DetailView``:

.. list-table::
   :header-rows: 1

   * - HTTP method
     - Action
     - Calls on the pipeline
   * - ``GET``
     - ``Actions.read``
     - ``read(id=id)``
   * - ``PATCH``
     - ``Actions.update``
     - ``read(id=id)``, then ``update(resource=resource, data=data)``
   * - ``DELETE``
     - ``Actions.destroy``
     - ``read(id=id)``, then ``destroy(resource=resource)``

``ListView``:

.. list-table::
   :header-rows: 1

   * - HTTP method
     - Action
     - Calls on the pipeline
   * - ``GET``
     - ``Actions.list``
     - ``list(filters=..., sorting=..., pagination=...)``, once; the pagination links use its total
   * - ``POST``
     - ``Actions.create``
     - ``create(data=data)``

In every method the allowed action is checked first, then the guards, then the request is parsed and only then
the pipeline is called. See :ref:`the request flow <layers-request-flow>`, and :ref:`layers-actions` for the
methods of every action.

``PATCH`` removes the ``id`` from the body before it reaches ``update``: the object is identified by ``resource``.
A body ``id`` that differs from the URL is rejected with ``409`` before anything is loaded.

Pagination links
----------------

For a request with ``page[size]`` and ``page[number]``, ``ListView`` builds the pagination links from the ``total``
of the ``ListResult``. When the total is ``None``, ``last`` is ``null`` and ``next`` is present only for a full
page, so a short page has no ``next`` link. See :ref:`layers-list-results`.

The links come from the view's ``pagination`` attribute, a ``flask_jsonapi.query_string.SizeNumberPagination`` by
default. To change them, set ``pagination`` on a ``ListView`` subclass and name that subclass in the ViewSet's
``list_view_class``. A custom pagination class implements three methods:

* ``parse()`` returns a dict with ``size`` and ``number``, or an empty dict when the request asks for no page.
* ``get_links(page_size, current_page, total_count)`` is used when the total is known.
* ``get_links_without_total(page_size, current_page, item_count)`` is used when it is ``None``. ``item_count``
  is the number of objects on the current page.

Both link methods return a dict with ``self``, ``first``, ``previous``, ``next`` and ``last``, holding ``None``
for a page that does not exist.

Errors
------

Exceptions of the data service are translated to JSON:API errors in the view, for every action. See :ref:`layers-errors` for the table.

Calling a data service directly
-------------------------------

The pipeline is a data service itself, so code outside HTTP can use the same layers. ``build_pipeline`` takes a
list of layers, outermost first, and the data service. The view builds its pipeline as
``build_pipeline([object_permissions, *middlewares], data_service)``, leaving out ``object_permissions`` when it is
``None``:

.. code-block:: python

    from flask_jsonapi import middlewares

    pipeline = middlewares.build_pipeline([OnlyPublished()], ArticleRepository())
    articles = pipeline.list(filters={}, sorting=[], pagination=None).items

``list`` returns a ``ListResult``: ``items`` holds the objects, and ``total`` is ``None`` here because no page is
requested.
