# Component Variant Matrix

This example models a visual rendering surface rather than a backend workflow.

Imagine a book cover card partial with several enum-like attributes. The goal is not to write unit tests from the rows directly. The goal is to generate a compact, deterministic set of variants that a harness can render into a contact sheet, screenshot, visual diff suite, or manual design review.

The evaluator could be:

- a Rails preview page
- a Storybook story
- a Playwright screenshot run
- a generated contact sheet
- a visual diff service

The important shape is the same as a code test surface: finite parameters, real constraints, and generated rows that cover interactions without rendering every possible combination.
