## Run tests

### 1. Install nose

```pip install nose```

### 2. Run tests

From the project directory ```animl-email-relay```

```nosetests```

Show the output of print statements

```nosetests -s```

Run specific test file

```nosetests -s tests.test_handler```

Run specific TestCase

```nosetests -s tests.test_handler:ExampleTestCase```

Run specific test

```nosetests -s tests.test_handler:ExampleTestCase.test_example```

I am using the standard library unittest. There are more fancy approaches, that
help with setting up mocked environments or provide packet specific assertion
and object construction methods. In our context
https://botocore.amazonaws.com/v1/documentation/api/latest/reference/stubber.html
is very interesting.
