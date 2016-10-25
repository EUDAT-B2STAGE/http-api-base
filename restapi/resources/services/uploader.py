# -*- coding: utf-8 -*-

"""
Upload data to APIs.

Interesting reading:
http://flask.pocoo.org/docs/0.11/patterns/fileuploads/
https://philsturgeon.uk/api/2016/01/04/http-rest-api-file-uploads/

Note:
originally developed for POST,
should/could be used also for PUT
http://stackoverflow.com/a/9533843/2114395

"""

import os
# import shutil
# import subprocess as shell
from flask import request, send_from_directory
from werkzeug import secure_filename
import commons.htmlcodes as hcodes
from commons.logs import get_logger

from ...confs.config import UPLOAD_FOLDER

logger = get_logger(__name__)


######################################
# Save files http://API/upload
class Uploader(object):

    allowed_exts = []
    # allowed_exts = ['png', 'jpg', 'jpeg', 'tiff']

    def split_dir_and_extension(self, filepath):
        filebase, fileext = os.path.splitext(filepath)
        return filebase, fileext.strip('.')

    def allowed_file(self, filename):
        if len(self.allowed_exts) < 1:
            return True
        return '.' in filename \
            and filename.rsplit('.', 1)[1].lower() in self.allowed_exts

    @staticmethod
    def absolute_upload_file(filename, subfolder=None, onlydir=False):
        if subfolder is not None:
            filename = os.path.join(subfolder, filename)
            dir = os.path.join(UPLOAD_FOLDER, subfolder)
            if not os.path.exists(dir):
                os.mkdir(dir)
        abs_file = os.path.join(UPLOAD_FOLDER, filename)  # filename.lower())
        if onlydir:
            return os.path.dirname(abs_file)
        return abs_file

    def download(self, filename=None, subfolder=None, get=False):

        if not get:
            return self.response(
                "No flow chunks for now", code=hcodes.HTTP_OK_ACCEPTED)

        if filename is None:
            return self.force_response(errors={
                "Missing file": "No filename specified to download"})

        path = self.absolute_upload_file(
            filename, subfolder=subfolder, onlydir=True)
        logger.info("Provide '%s' from '%s' " % (filename, path))

        return send_from_directory(path, filename)

    def upload(self, subfolder=None, force=False):

        if 'file' not in request.files:
            return self.force_response(errors={
                "Missing file": "No files specified"})

        myfile = request.files['file']

        # ## IN CASE WE WANT TO CHUNK
        # ##parser = reqparse.RequestParser()
        # &flowChunkNumber=1
        # &flowChunkSize=1048576&flowCurrentChunkSize=1367129
        # &flowTotalSize=1367129
        # &flowIdentifier=1367129-IMG_4364CR2jpg
        # &flowFilename=IMG_4364.CR2.jpg
        # &flowRelativePath=IMG_4364.CR2.jpg
        # &flowTotalChunks=1

        # Check file extension?
        if not self.allowed_file(myfile.filename):
            return self.force_response(errors={
                "Wrong extension": "File extension not allowed"})

        # Check file name
        filename = secure_filename(myfile.filename)
        abs_file = self.absolute_upload_file(filename, subfolder)
        logger.info("File request for [%s](%s)" % (myfile, abs_file))

        # ## IMPORTANT NOTE TO SELF:
        # If you are going to receive chunks here there could be problems.
        # In fact a chunk will truncate the connection
        # and make a second request.
        # You will end up with having already the file
        # But corrupted...
        if os.path.exists(abs_file):

            logger.warn("Already exists")
            if force:
                os.remove(abs_file)
                logger.debug("Forced removal")
            else:
                return self.force_response(
                    errors={
                        "File '" + filename + "' already exists.":
                        "Change file name or use the force parameter",
                    }, code=hcodes.HTTP_BAD_REQUEST)

        # Save the file
        try:
            myfile.save(abs_file)
            logger.debug("Absolute file path should be '%s'" % abs_file)
        except Exception:
            return self.force_response(errors={
                "Permissions": "Failed to write uploaded file"},
                code=hcodes.HTTP_DEFAULT_SERVICE_FAIL)

        # Check exists
        if not os.path.exists(abs_file):
            return self.force_response(errors={
                "Server file system": "Unable to recover the uploaded file"},
                code=hcodes.HTTP_DEFAULT_SERVICE_FAIL)

        # Extra info
        ftype = None
        fcharset = None
        try:
            # Check the type
            from plumbum.cmd import file
            out = file["-ib", abs_file]()
            tmp = out.split(';')
            ftype = tmp[0].strip()
            fcharset = tmp[1].split('=')[1].strip()
        except Exception:
            logger.warning("Unknown type for '%s'" % abs_file)

        ########################
        # ## Final response

        # Default redirect is to 302 state, which makes client
        # think that response was unauthorized....
        # see http://dotnet.dzone.com/articles/getting-know-cross-origin

        return self.force_response({
            'filename': filename,
            'meta': {'type': ftype, 'charset': fcharset}
        }, code=hcodes.HTTP_OK_BASIC)

    def remove(self, filename, subfolder=None, skip_response=False):
        """ Remove the file if requested """

        abs_file = self.absolute_upload_file(filename, subfolder)

        # Check file existence
        if not os.path.exists(abs_file):
            logger.critical("File '%s' not found" % abs_file)
            return self.force_response(errors={
                "File missing": "File requested does not exists"},
                code=hcodes.HTTP_BAD_NOTFOUND)

        # Remove the real file
        try:
            os.remove(abs_file)
        except Exception:
            logger.critical("Cannot remove local file %s" % abs_file)
            return self.force_response(errors={
                "Permissions": "Failed to remove file"},
                code=hcodes.HTTP_DEFAULT_SERVICE_FAIL)
        logger.warn("Removed '%s' " % abs_file)

        if skip_response:
            return

        return self.force_response("Deleted", code=hcodes.HTTP_OK_BASIC)
