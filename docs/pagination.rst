Pagination
==========

Flask-jsonapi supports page-based pagination.
[`specification <http://jsonapi.org/format/#fetching-pagination>`__]

By default list endpoint results are not paginated.

Usage
~~~~~

.. code-block:: bash

    /users?page[size]={page_size}&page[number]={page_number}