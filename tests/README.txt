Before the test can be run:

    Create a file called test.cfg in the test sub-direstory, and add the RTM api_key and secret, like this:
    [auth]
    api_key=many characters
    secret=many characters

    Edit the file test_cow_rest.py, and change AUTH_TEST = False to AUTH_TEST = True

    Change to virtualenv mycroft to fulfill requirements

    Run the unittests in test_cow_rest.py
    It will write an authentication link in the console. Click on the link, and authenticate in a browser. After authentication in the browser hit return in the unitest console.
    The test should succeed

    Edit the file test_cow_rest.py, and reset AUTH_TEST = True back to AUTH_TEST = False
