#!/bin/bash

echo "Launching tests with coverage"
sleep 2

nosetests --with-coverage \
    --cover-erase --cover-package=restapi \
    --cover-html --cover-html-dir=/tmp/coverage
