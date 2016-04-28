#!/bin/bash

echo "Launching tests with coverage"
sleep 2

nosetests --with-coverage --cover-package=restapi
