from django.apps import AppConfig


class RecommendApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "recommend_api"

    def ready(self):
        # Register checks without querying the database.Needed so
        # ones like `@register("dataset", deploy=True)` can run.
        from . import checks
