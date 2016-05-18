#!/bin/bash

echo "Launching tests with coverage"
sleep 1

# nosetests \
#     --stop \
#     --with-coverage \
#     --cover-erase --cover-package=restapi \
#     --cover-html --cover-html-dir=/tmp/coverage

# Coverage + stop on first failure
com="nose2 -F"
option="-s test"
cov_options="--quiet -C --coverage-report term --coverage-report html"

# Basic tests, written for the http-api-base sake
$com $option/base
if [ "$?" == "0" ]; then
    # Custom tests from the developer, if available
    $com $option/custom
    if [ "$?" == "0" ]; then
        # Print coverage if everything went well so far
        $com $cov_options $option/custom
    fi
fi
