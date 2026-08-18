# apps/common/pagination.py

from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """Page-number pagination that actually honours ``?page_size=``.

    The project-wide default (``rest_framework.pagination.PageNumberPagination``)
    leaves ``page_size_query_param`` as ``None``, which means every
    ``?page_size=`` sent by a client is silently discarded and the response is
    hard-capped at ``PAGE_SIZE`` (20). Views that serve directory-style lists
    opt into this class instead.

    Mirrors ``digicrm/common/pagination.py`` so both services behave the same.
    """

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 500
