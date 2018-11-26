Sorting
=======

Flask-jsonapi supports sorting by one or more criteria .
[`specification <https://jsonapi.org/format/#fetching-sorting>`__]

**Note:**

To enable sorting by a "sort field" other than resource attributes, you need to specify this field in the schema and implement sorting method in the repository.

Usage
~~~~~

.. code-block:: bash

    /articles?sort=-created,title
