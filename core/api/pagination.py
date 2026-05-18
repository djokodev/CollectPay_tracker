from decouple import config
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    page_size = config("API_PAGE_SIZE", default=20, cast=int)
    page_size_query_param = "page_size"
    max_page_size = config("API_MAX_PAGE_SIZE", default=100, cast=int)
