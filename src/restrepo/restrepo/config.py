# encoding=utf8
#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#


import os


SCHEME = 'https'

THIS_DIR = os.path.abspath(os.path.dirname(__file__))

ARCHIVE_IDS = ('archive_id', 'archiveFile')  # these two items together identify an archiveFile

# subdirectory of the images loction, where cached thumbnails are stored
CACHE_SUBDIRECTORY = 'cache'
SERVICE_SCAN_COLLECTION = '/scans'
SERVICE_SCAN_COLLECTION_CSV = '/scans.csv'
SERVICE_SCAN_ITEM = '/scans/{number}'
SERVICE_SCAN_ITEM_DEFAULT_IMAGE = '/scans/{number}/image'
SERVICE_SCAN_IMAGES_COLLECTION = '/scans/{number}/images'
SERVICE_SCAN_IMAGES_ITEM = '/scans/{number}/images/{number_of_image}'
SERVICE_SCAN_IMAGES_ITEM_RAW = '/scans/{number}/images/{number_of_image}/{file_with_arbitrary_hash_value}'
SERVICE_EAD_COLLECTION = '/ead'
SERVICE_EAD_ITEM = '/ead/{ead_id}'
SERVICE_EAD_ITEM_RAW = '/ead/{ead_id}/file'
SERVICE_COMPONENTS_COLLECTION = '/lists/components'
SERVICE_COMPONENT_TREE = '/lists/componentTree'
SERVICE_GET_COMPONENT_FOR_VIEWER = '/lists/get_component_for_viewer'
LOG_SERVICE_PATH = '/log'
LIST_SERVICE_PATH = '/lists'
SERVICE_ARCHIVE_COLLECTION = '/lists/archives'
SERVICE_ARCHIVE_ITEM = '/lists/archives/{archive_id}'
SERVICE_ARCHIVEFILE_COLLECTION = '/archivefiles'
SERVICE_ARCHIVEFILE_ITEM = '/archivefiles/{archive_id}/{archiveFile}'
SERVICE_FINDINGAID_COLLECTION = '/lists/findingaid'
SERVICE_PAGEBROWSER_BOOK = '/pagebrowser/{archive_id}/{archiveFile}'
SERVICE_PAGEBROWSER_PAGELIST = SERVICE_PAGEBROWSER_BOOK + '/pagelist'
SERVICE_UTILS_SCAN_DELETE = '/utils/delete_scans'
SERVICE_ERROR = '/error'

# next one is deprecated
SERVICE_ARCHIVE_FILE_ID = '/lists/archiveFileId'

# the default status fo the archive file, if we don't know any better, is 'public'
STATUS_NEW = 1
STATUS_PUBLISHED = 2

DEFAULT_ARCHIVEFILE_STATUS = STATUS_NEW

PARAM_ARCHIVE_ID = """
        * **archive_id:**
            an id of an archive, must be in %(SERVICE_ARCHIVE_COLLECTION)s
""" % globals()

PARAM_STATUS = """
        * **status:**
            optional: a value among :ref:`status_values` (except 0)
"""

#
# do a soft_commit on solr for optimizing response time in critical places
#
OPTIMIZATION_SOFT_COMMIT = True

FN_EAD2VIEWER_MAPPING = os.path.join(THIS_DIR, 'data', 'ead2viewer_mapping.csv')


class status(object):
    DELETED = 0
    NEW = STATUS_NEW
    PUBLISHED = STATUS_PUBLISHED


#
# ERRORS stores all possible errors
#
# Todo: incorporate in documeantion
#
class Error:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class Errors(object):
    _ERROR_CODES = [
        'archive_missing_value_archive',
        'archive_missing_value_institution',
        'archive_has_scans',
        'archive_has_eads',
        'archive_exists',
        'archive_not_found',
        'xml_syntax_error',
        'xml_dtd_validation_error',
        'instititution_not_found',
        'ead_error',
        'ead_exists',
        'ead_invalid_id',
        'ead_not_found',
        'missing_parameter',
        'invalid_parameter',
        'invalid_file',
        'duplicate_archive_ids',
        'missing_file',
        'cant_delete_last_scan_image',
        'archivefile_has_eads',
        'archivefile_has_scans',
        'archivefile_notfound',
    ]

    _ERROR_CODES = dict((code, {'name': code}) for code in _ERROR_CODES)

    def __init__(self):
        for key in self._ERROR_CODES:
            setattr(self, key, Error(**self._ERROR_CODES[key]))


ERRORS = Errors()


def update_docstrings(d):
    for obj in d.values():
        if (type(obj) is type(update_docstrings)):
            if obj.__doc__:
                obj.__doc__ = obj.__doc__ % globals()
