#!/bin/bash

echo "Launching tests with coverage"
sleep 2

<<<<<<< HEAD
nosetests \
    --stop \
    --with-coverage \
    --cover-erase --cover-package=restapi \
    --cover-html --cover-html-dir=/tmp/coverage
=======
nose2 --with-coverage
>>>>>>> f3ec335e6aba7c39086c10cebaef75ab9bf49352
