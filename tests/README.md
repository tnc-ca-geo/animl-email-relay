## Unit tests

I switched to using pytest as testrunner since nobodody seems to use
Nose anymore. It has not been maintained for awhile. But, I am sticking
to the mocking capabilities of the Python unittest library so any Python
testrunner should work. So there should not be any functionality or fixtures
specific to pytest. See https://docs.pytest.org/en/7.3.x/

### 1. Install Pytest

```pip install pytest```

### 2. Run tests

From the project directory ```animl-email-relay```

```pytest```

Show the output of print statements

```pytest -s```

Run specific test file

```pytest tests/test_handler.py```

Run specific TestCase

```pytest tests/test_handler.py::TestFullHandler```

Run specific test

```
pytest tests.test_handler::TestFullHandler.test_handler_ridgetectest_example
```
