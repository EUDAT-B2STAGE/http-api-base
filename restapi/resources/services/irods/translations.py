# -*- coding: utf-8 -*-

"""
Converting irods data into GraphDB models
"""

import os
from commons.logs import get_logger

logger = get_logger(__name__)


class DataObjectToGraph(object):

    def __init__(self, graph, icom):
        self._graph = graph
        self._icom = icom

    def ifile2nodes(self, ifile):

        ##################################
        # Getting the three pieces from Absolute Path of data object:
        # zone, absolute path and filename
        # also keeps track of collections
        zone = ""
        irods_path = ""
        collections = []
        (prefix, filename) = os.path.split(ifile)
        while prefix != "/":
            oripath = prefix
            # Note: THIS IS NOT IRODS_PATH AS EUDAT THINKS OF IT
            irods_path = os.path.join(zone, irods_path)
            # Split into basename and dir
            (prefix, zone) = os.path.split(prefix)
            # Skip the last one, as it is a Zone and not a collection
            if zone != oripath.strip('/'):
                # Save collection name (zone) and its path (prefix+zone)
                collections.append((zone, oripath))

## // TO FIX: disabled for now
        # # Eudat URL
        # location = self._icom.current_location(ifile)
        # logger.debug("Location: %s" % location)
        location = "Unknown"

        ##################################
        # Store Zone node
        current_zone = self._graph.Zone.get_or_create({'name': zone}).pop()

        ##################################
        # Store Data Object

        # Prepare properties
        properties = {
## // TO FIX: avoid duplicates
            # 'location' :location,
            'filename': filename,
            'path': ifile,
        }
        # Build UUID
        current_dobj = self._graph.createNode(
            self._graph.DataObject, properties)
        # Connect the object
        current_dobj.located.connect(current_zone)
        logger.info("Created and connected data object %s" % filename)

        ##################################
        # Get Name and Store Resource node
        resources = self._icom.get_resource_from_dataobject(ifile)

        for resource_name in resources:
            logger.debug("Resource %s" % resource_name)
            current_resource = \
                self._graph.Resource.get_or_create(
                    {'name': resource_name}).pop()
            # Connect resource to Zone
## // TO FIX: only if not connected already?
            current_resource.hosted.connect(current_zone)
            # Connect data object to this replica resource
            current_dobj.stored.connect(current_resource)

        ##################################
        # Store Collections

        collection_counter = 0
        last_collection = None
        # print("Collections", collections)

        for collection, cpath in collections:

            collection_counter += 1
            logger.debug("Collection %s" % collection)
            # print("COLLECTON", collection, cpath)
            properties = {
                'path': cpath,
                'name': collection,
            }
            current_collection = \
                self._graph.Collection.get_or_create(properties).pop()

            # Link the first one to dataobject
            if collection_counter == 1:
                current_dobj.belonging.connect(current_collection)

            # Link to zone
            # if collection_counter == len(collections):
            current_collection.hosted.connect(current_zone)

            # Otherwise connect to the previous?
            if last_collection is not None:
                current_collection.matrioska_from.connect(last_collection)

            last_collection = current_collection
            logger.debug("Last collection: %s", last_collection)
