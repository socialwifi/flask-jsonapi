Including relationships
=======================

Flask-jsonapi supports inclusion of related resources.
[`specification <https://jsonapi.org/format/#fetching-includes>`__]

**Note:**

By default when ``include`` parameter is not provided, marshmallow-jsonapi doesn't serialize resource linkage. You can enable it by passing ``include_resource_linkage=True`` and the resource ``type_`` argument to the desired fields in schema.
[`documentation <https://marshmallow-jsonapi.readthedocs.io/en/latest/quickstart.html?highlight=include_resource_linkage#resource-linkages>`__]

Usage
~~~~~

Inclusion of related resource in compound document in could be requested as shown below:

.. code-block:: bash

    /articles/1?include=comments

Inclusion of resources related to other resources can be achieved using a dot-separated path:

.. code-block:: bash

    /articles/1?include=comments.author

Multiple related resources can be requested in a comma-separated list:

.. code-block:: bash

    /articles/1?include=author,comments.author
