# ADR-002: Cache Analysis Targets Production

**Date:** 2026-08-25
**Status:** Accepted

---

## Context

TasteMender intentionally disables caching in development and test environments to
preserve fast iteration and test isolation. This can distract from questions about
the deployed application's cache behavior.

## Decision

When evaluating or changing caching behavior, use the production configuration as
the default target. Discuss development and test cache behavior only when it is
directly relevant to the question.

## Rationale

- Production cache behavior determines user-visible performance and resource use.
- Development and test cache bypasses are intentional environment-specific behavior.
- A production-first default keeps cache discussions focused and avoids repeating
  known development limitations.

## Consequences

- Cache-related changes and reviews should first verify the production cache backend,
  middleware, timeout, and cache-key behavior.
- Development and test cache configuration remains relevant for debugging or test
  design, but is not the default analysis target.