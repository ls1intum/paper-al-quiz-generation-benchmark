---
title: Testing
sidebar_position: 3
---

# Testing

This project uses **pytest** for automated tests.

## Run Tests

```bash
pytest
```

## Run Tests With Coverage

```bash
pytest --cov=src --cov-report=term-missing
```

## Writing Tests

### Key Principles

- **No external LLM calls**: tests must never hit OpenAI/Anthropic/Azure or any networked model.
- **Deterministic**: avoid randomness and time-based assertions; tests should be stable across runs.
- **Behavior > quality**: assert functional behavior (counts, outputs, validation), not model quality.

### Mocking LLMs

Use the test mock provider from `tests/conftest.py`:

- `MockLLMProvider` implements `LLMProvider.generate` and returns deterministic numeric strings.
- `mock_llm_provider` fixture registers it via `LLMProviderFactory` for tests.

When writing tests that involve evaluation runs:
1. Include the `mock_llm_provider` fixture.
2. Register metrics via the `registered_metrics` fixture.
3. Use `sample_config`/`sample_quiz` fixtures where possible.

### Test Structure

- **Unit tests**: models, metrics, registry, config loader (no IO, no runner).
- **Component tests**: runner orchestration with mocked LLMs.
- **IO/analysis tests**: file round-trips and aggregation/reporting with fixed inputs.

### What to Test

- **Validation**: input schema errors, config validation, parameter validation.
- **Control flow**: skip behavior for missing metrics/evaluators, run counts, metric counts.
- **Parsing**: metric response parsing success/failure cases.
- **Aggregation/reporting**: stats computed correctly for fixed scores.

### What Not to Test

- **Provider implementations** (OpenAI/Anthropic/Azure): skip to avoid accidental network usage.
- **LLM output quality**: do not assert on semantic content beyond numeric parsing.
