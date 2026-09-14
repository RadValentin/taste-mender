# Testing Methodology

## General guidelines
Tests should support fast iteration, never get in the way of development, not feel like a chore and be easy to comprehend. In general the following guidelines should apply:

- Avoid testing implementation details: checking for strings in API responses or inside components, CSS or snapshots, toggle states, and in general any trivial piece of functionality.
- Related tests (e.g. same endpoint) can be grouped under a single suite and they can share a common mock or fixture.
- Suites should be split when a subset of tests require making changes to the shared mock or fixture.
- Coverage should mean testing the scenarios and failure modes a piece of code can encounter. This should be the upper bound and goal of all testing. Think of the coverage report as the lower bound, e.g. 100% coverage means we've tested every single line at least once.

## Back-end
API tests use Django's test runner and DRF's `APITestCase`. They exercise the endpoints through Django's test client, using factory-generated database records where the response depends on persisted data.

From `backend/`, run the complete suite with:

```bash
python manage.py test
```

To run one API test module or class, provide its dotted path, for example:

```bash
python manage.py test recommend_api.tests.api.test_search_api
python manage.py test recommend_api.tests.api.test_search_api.SearchAPITests
```

API tests should focus on endpoint contracts: status codes, validation errors, response shapes, pagination, filtering, relationships, and important edge cases.

Use `SimpleTestCase` for endpoint tests that do not need database records, such as public files and URL routing.

## Front-end
Note: FE is in the prototype stage at the time of writing. Tests would only get in the way especially since things are bound to change massively. Re-evaluate this decision periodically.