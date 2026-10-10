# Enrichments

This package owns optional, independently refreshable data applied after the
core dataset exists, such as prefilling external source caches.

Enrichment jobs should remain incremental, resumable, and independent of the
core database rebuild.