# Tests

Test suite for Barbossa components.

## Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_linear_client.py

# Run with coverage
python -m pytest --cov=src/barbossa tests/
```

## Test Files

- `test_linear_client.py` - Linear API integration tests
- `test_issue_tracker.py` - Issue tracker abstraction tests

## Writing Tests

When adding new functionality:

1. Create test file: `test_<module_name>.py`
2. Use pytest fixtures for setup/teardown
3. Mock external API calls (GitHub, Linear, Anthropic)
4. Test both success and error cases

## Test Coverage

We aim for:
- 80%+ coverage on utility modules
- 60%+ coverage on agent modules (harder to test LLM interactions)
- 100% coverage on critical paths (issue tracking, config parsing)
