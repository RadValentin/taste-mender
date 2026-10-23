# ADR-004: Disabled lint rules

**Date:** 2026-10-23
**Status:** Accepted

---

## Context

Linting is most useful when it doesn't significantly impede development. We DON'T make changes to keep the linter happy, because someone said so online, etc. We make changes because the linter identified a real problem.

## Decision

Linting rules can be disabled if they go against standard patterns or if they require making changes when there's no valid reason to do so, other than satisfying the linter.

### Disable `@eslint-react/set-state-in-effect`

This rule is overly strict. Changing the state inside an effect is a common pattern and it's also something that the official React docs teach. There is no value in keeping this rule enabled.

Issue on React repo, mentioning this: https://github.com/react/react/issues/34743