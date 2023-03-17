from . import constants
from django.core.paginator import Paginator


def page_nav(posts, request):
    paginator = Paginator(posts, constants.POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
