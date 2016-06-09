#!/bin/bash

echo "Launching tests with coverage"
sleep 1

# Avoid colors when saving tests output into files
export TESTING_FLASK="True"

# nosetests \
#     --stop \
#     --with-coverage \
#     --cover-erase --cover-package=restapi \
#     --cover-html --cover-html-dir=/tmp/coverage

# Coverage + stop on first failure
com="nose2 -F"
option="-s test"
cov_reports=" --coverage-report term --coverage-report html"
cov_options="-C --coverage restapi $cov_reports"

# Basic tests, written for the http-api-base sake
$com $option/base --log-capture
if [ "$?" == "0" ]; then
    # Custom tests from the developer, if available
    $com $option/custom --log-capture
    if [ "$?" == "0" ]; then
        # Print coverage if everything went well so far
        $com --output-buffer $cov_options 2> /tmp/logfile.txt
        grep "platform linux" -A 1000 /tmp/logfile.txt
    else
        exit $?
    fi
else
    exit $?
fi
