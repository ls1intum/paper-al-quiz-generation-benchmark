---
title: Troubleshooting
sidebar_position: 6
---

## Troubleshooting

### Common Issues

#### "Module not found" errors

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

#### API Key errors

**Symptoms**: `AuthenticationError`, `Invalid API key`

**Solutions**:
1. Verify `.env` file is in project root
2. Check API keys are correct (no extra spaces)
3. Ensure provider in YAML matches `.env` configuration
4. Test API key manually with provider's playground

#### No quizzes found

**Symptoms**: `Loaded 0 quizzes`

**Solutions**:
1. Verify quiz JSON files are in correct directory
2. Check JSON format validity: `python -m json.tool data/quizzes/quiz.json`
3. Ensure `source_material` field references existing file
4. Review directory paths in config YAML

#### High variance in results

**Symptoms**: Std dev > 10

**Possible causes**:
- Ambiguous metric prompts
- Complex questions with multiple interpretations
- Insufficient runs

**Solutions**:
- Increase number of runs (5-10)
- Refine metric prompt for clarity
- Review raw LLM responses for patterns
- Try different evaluator models

#### Unexpected scores

**Symptoms**: Scores don't match manual assessment

**Diagnostic steps**:
1. Review raw LLM responses in `<run-bundle>/results.json`
2. Test metric prompt manually in LLM playground
3. Verify source material quality and completeness
4. Check if questions align with learning objectives
5. Compare across multiple evaluators

#### API rate limit errors

**Symptoms**: `RateLimitError`, `429 Too Many Requests`

**Solutions**:
- Add delays between API calls (implement in provider)
- Use batch processing with smaller batches
- Check your tier limits with provider
- Spread evaluation across longer time period

#### Memory issues

**Symptoms**: `MemoryError`, system slowdown

**Solutions**:
- Process quizzes in batches
- Reduce `max_tokens` in config
- Use lighter models (gpt-3.5-turbo vs gpt-4)
- Clear results between runs

---
