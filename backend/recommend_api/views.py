from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import render
from django.views.generic import View
from .models import *


def robots_txt(request):
    return HttpResponse(
        "User-agent: *\n"
        "Allow: /\n\n"
        "Sitemap: https://taste-mender.com/sitemap.xml\n",
        content_type="text/plain",
    )


class SPAView(View):
    """
    View that serves the front-end Single Page App
    """

    status_code = 200

    def get(self, request, *args, **kwargs):
        index = settings.BASE_DIR.parent / "frontend" / "dist" / "index.html"

        if index.exists():
            return FileResponse(open(index, "rb"), status=self.status_code)

        raise Http404("Build not found. Run `npm run build` in /frontend.")
