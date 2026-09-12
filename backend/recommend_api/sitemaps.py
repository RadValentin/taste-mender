from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class PublicPagesSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.7

    def items(self):
        return ["api:home-page", "api:search-page"]

    def location(self, item):
        return reverse(item)


sitemaps = {"public": PublicPagesSitemap}