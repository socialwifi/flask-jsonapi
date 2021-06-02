Sparse Fieldsets
================

Flask-jsonapi supports ``fields[TYPE]`` parameter to restrict the server to return a set of fields for a given resource type.
[`specification <https://jsonapi.org/format/#fetching-sparse-fieldsets>`__]

**Note:**

By default when ``include`` parameter is not provided, marshmallow-jsonapi doesn't serialize resource linkage. You can enable it by passing ``include_resource_linkage=True`` and the resource ``type_`` argument to the desired fields in schema.
[`documentation <https://marshmallow-jsonapi.readthedocs.io/en/latest/quickstart.html?highlight=include_resource_linkage#resource-linkages>`__]

Usage
~~~~~

Basic example:

.. code-block:: bash

    /articles?fields[articles]=title,body

This example demonstrates combination on both ``include`` and ``fields`` parameters.

.. code-block:: bash

    /articles?include=author&fields[articles]=title,body&fields[people]=name

**Note:**

For ``include`` parameter there are specific `attributes` of the resources are provided, but for ``fields`` parameter there are `types` provided.
