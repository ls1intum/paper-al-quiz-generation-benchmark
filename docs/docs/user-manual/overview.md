---
title: Overview
sidebar_position: 1
---

# Quiz Generation Benchmark

**A Framework for Evaluating Quizzes Using LLMs as Judges**

---

## Overview

This benchmark framework provides a rigorous, extensible approach to evaluating quiz questions using multiple LLM-based quality metrics. The system is **stateless**, **modular**, and designed for **extensibility** and **reproducibility**.

### What This Framework Does

Systematically evaluate the quality of quizzes using research-backed metrics:

- **Alignment with Learning Objectives**: Ensure questions assess intended outcomes
- **Cognitive Level Appropriateness**: Evaluate Bloom's taxonomy levels
- **Clarity and Precision**: Assess linguistic quality and unambiguity
- **Answer Key Correctness**: Verify single correct answer and clear distractors
- **Distractor Quality**: Evaluate plausibility based on common misconceptions
- **Homogeneous Options**: Check parallel structure across answer choices
- **Absence of Cueing**: Detect inadvertent clues to correct answers
- **Grammatical Correctness**: Ensure proper language usage throughout

### Key Features

✅ **Multiple LLM Support** — Azure OpenAI, OpenAI API, Anthropic Claude, Ollama, and OpenAI-compatible local models  
✅ **Research-Based Metrics** — Implements quality criteria from assessment literature  
✅ **Flexible Configuration** — YAML-based configs for easy experimentation  
✅ **Statistical Rigor** — Multiple runs with aggregation (mean, median, standard deviation)  
✅ **Reproducible Results** — Versioned configs, deterministic evaluation (temperature=0.0)  
✅ **Clean Architecture** — Type-safe Python with clear interfaces  
✅ **Production-Oriented** — Complete with examples, tests, and comprehensive documentation

### Terminology

| Term | Definition |
|------|------------|
| **Metric** | A measurement of quiz quality (e.g., alignment, clarity, distractor quality) |
| **Evaluator** | An LLM provider that executes metric assessments |
| **Benchmark Run** | A complete evaluation cycle with specific configuration |
| **Quiz** | A collection of questions generated from source material |
| **Question** | Individual quiz item (multiple-choice, single-choice, true/false) |
| **Distractor** | An incorrect answer option designed to identify misconceptions |

---

## System Goals

1. **Evaluate quiz quality** using configurable, research-based metrics
2. **Support multiple LLM providers** (Azure OpenAI, OpenAI, Anthropic, Ollama, open-source)
3. **Enable flexible configuration** for different benchmark runs and research questions
4. **Provide reproducible results** with versioning, statistical aggregation, and deterministic evaluation
5. **Maintain clean architecture** with clear interfaces, type safety, and extensibility

---
