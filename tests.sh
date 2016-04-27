#!/bin/bash

echo "Launching tests with coverage"
sleep 2
nosetests --cover-branches --with-coverage --cover-erase --cover-package=restapi --cover-html