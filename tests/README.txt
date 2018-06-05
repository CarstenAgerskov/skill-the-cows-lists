Before the test can be run:

    Create a file called test.cfg in the test sub-direstory, and add the RTM
    api_key and secret, like this:
    [auth]
    api_key=many characters
    secret=many characters

    Change to virtualenv mycroft to fulfill requirements:
        cd <your mycroft-core directory>
        # When using bash/zsh use source as shown below, otherwise consult the venv documentation
        source .venv/bin/activate

    Run the unit tests in test_cow_rest.py

    If you didn't already authenticate with remember the milk, only unit tests
    on authentication will run. It will write an authentication link in the
    console. Click on the link, and authenticate in a browser. After
    authentication in the browser hit return in the unitest console. The test
    should succeed, and authentication is done.

    After authentication unit tests will run when test_cow_rest.py is called

