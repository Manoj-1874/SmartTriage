# Testing Guide for SmartTriage Dashboard

This document explains how to run tests for the SmartTriage Dashboard application.

## Prerequisites

Make sure you have installed all development dependencies:

```bash
pip install -r requirements.txt
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Tests with Coverage Report

```bash
pytest --cov=. --cov-report=html
```

This will generate a coverage report in `htmlcov/index.html`.

### Run Specific Test Files

```bash
# Run only validation tests
pytest tests/test_validation.py

# Run only route tests
pytest tests/test_routes.py
```

### Run Tests by Marker

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### Run Tests with Verbose Output

```bash
pytest -v
```

### Run Tests and Stop on First Failure

```bash
pytest -x
```

### Run Tests in Parallel (faster)

```bash
pip install pytest-xdist
pytest -n auto
```

## Test Structure

```
tests/
├── conftest.py           # Test configuration and fixtures
├── test_validation.py    # Unit tests for validation utilities
├── test_routes.py        # Integration tests for API routes
└── test_database.py      # Tests for database operations (to be added)
```

## Test Fixtures

The following fixtures are available in `conftest.py`:

- `app`: Flask application configured for testing
- `client`: Test client for making requests
- `authenticated_client`: Pre-authenticated test client (as patient)
- `sample_triage_data`: Sample valid triage assessment data
- `sample_user_data`: Sample valid user registration data

## Writing New Tests

### Example Unit Test

```python
def test_validate_age():
    from utils.validation import VitalSignsValidator

    # Test valid age
    assert VitalSignsValidator.validate_age(25) == 25

    # Test invalid age
    with pytest.raises(ValidationError):
        VitalSignsValidator.validate_age(-1)
```

### Example Integration Test

```python
def test_login_success(client):
    # Register user
    client.post('/signup', data={
        'fullname': 'Test User',
        'email': 'test@example.com',
        'password': 'TestPass123',
        'role': 'patient'
    })

    # Login
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'TestPass123',
        'role': 'patient'
    }, follow_redirects=True)

    assert response.status_code == 200
```

## Test Coverage Goals

- **Validation utilities**: 100% coverage
- **API routes**: 90%+ coverage
- **Database operations**: 90%+ coverage
- **Overall application**: 80%+ coverage

## Continuous Integration

Tests should be run automatically on every commit using CI/CD:

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pytest --cov
```

## Troubleshooting

### Tests Fail Due to Missing Dependencies

```bash
pip install -r requirements.txt
```

### Tests Fail Due to Database Issues

The tests use an in-memory SQLite database. If you see database-related errors:

1. Check that `DATABASE_URL=sqlite:///:memory:` in test configuration
2. Ensure database tables are created in the `app` fixture

### Rate Limiting Issues in Tests

Rate limiting is disabled in testing mode. If you see rate limit errors:

1. Check `config.py` - `TestingConfig` should have `RATELIMIT_ENABLED = False`
2. Verify test is using the test configuration

## Best Practices

1. **Isolate tests**: Each test should be independent
2. **Use fixtures**: Leverage fixtures for common setup
3. **Test edge cases**: Include tests for invalid inputs
4. **Mock external services**: Don't rely on external APIs in tests
5. **Keep tests fast**: Unit tests should run in milliseconds
6. **Meaningful assertions**: Test behavior, not implementation

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [Flask testing documentation](https://flask.palletsprojects.com/en/latest/testing/)
- [Coverage.py documentation](https://coverage.readthedocs.io/)
