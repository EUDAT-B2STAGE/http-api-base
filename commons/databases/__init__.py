# -*- coding: utf-8 -*-

"""

This class should help creating Farm of any database/service instance
to be used inside a Flask server.

The idea is to have the connection check when the Farm class is instanciated.
Then the object would remain available inside the server global namespace
to let the user access a new connection.

"""

from __future__ import absolute_import
import abc
import time
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DBinstance(metaclass=abc.ABCMeta):

    def __init__(self, check_connection=False):

        if not check_connection:
            return

        name = self.__class__.__name__
        testdb = True
        counter = 0
        sleep_time = 1

        while testdb:
            try:
                obj = self.init_connection()
                del obj
                testdb = False
                logger.info("Instance of '%s' was connected" % name)
            except Exception as e:
                counter += 1
                if counter % 5 == 0:
                    sleep_time += sleep_time * 2
                logger.warning("%s: Not reachable yet. Sleeping %s."
                               % (name, sleep_time))
                logger.debug("Error was %s" % str(e))
                time.sleep(sleep_time)

    @abc.abstractmethod
    def init_connection(self):
        return

    @abc.abstractmethod
    def get_instance(self, *args):
        return
