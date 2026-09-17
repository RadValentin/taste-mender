from django.contrib.sitemaps.views import sitemap
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path, include, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from recommend_api.router import APIRouter
from recommend_api.sitemaps import sitemaps
from recommend_api import views
from recommend_api import api

router = APIRouter()
router.register(r"tracks", api.TrackViewSet, basename="track")
router.register(r"albums", api.AlbumViewSet, basename="album")
router.register(r"artists", api.ArtistViewSet, basename="artist")

app_name = "api"
urlpatterns = [
    path("api/v1/", include(router.urls)),
    path("api/v1/genres/", api.GenreView.as_view(), name="genre-list"),
    path("api/v1/recommend/", api.RecommendView.as_view(), name="recommend"),
    path("api/v1/search/", api.SearchView.as_view(), name="search"),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/swagger-ui/", SpectacularSwaggerView.as_view(url_name="api:schema"), name="swagger-ui"),
    path("api/v1/redoc/", SpectacularRedocView.as_view(url_name="api:schema"), name="redoc"),
]

# Keep explicit static URL patterns in all environments so static assets do not get redirected.
urlpatterns += staticfiles_urlpatterns()

# Handle requests for front-end views and specific files.
urlpatterns += [
    path("", views.SPAView.as_view(), name="home-page"),
    path("search", views.SPAView.as_view(), name="search-page"),
    path("robots.txt", views.robots_txt, name="robots-txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    # This must be last. It's a catch-all to set 404 status for unknown routes.
    re_path(
        r"^(?!api/|assets/|static/|admin/).*$",
        views.SPAView.as_view(status_code=404),
        name="spa-not-found"
    ),
]