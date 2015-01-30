from django.contrib.sitemaps import Sitemap
from cms.utils.moderator import get_page_queryset
from cms.models import Title

class CMSSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        page_queryset = get_page_queryset(None)
        all_pages = page_queryset.published()
        return Title.objects.filter(page__in=all_pages).order_by('language')

    def location(self, item):
        return "".join(["/", item.language,item.page.get_absolute_url(item.language)])

    def lastmod(self, item):
        return item.page.publication_date or item.page.creation_date
