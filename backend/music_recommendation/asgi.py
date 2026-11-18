"""
ASGI config for music_recommendation project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "music_recommendation.settings")

application = get_asgi_application()

from concurrent.futures import ThreadPoolExecutor
from recommend_api.checks import warn_dataset_mismatch

with ThreadPoolExecutor(max_workers=1) as executor:
    executor.submit(warn_dataset_mismatch).result()
