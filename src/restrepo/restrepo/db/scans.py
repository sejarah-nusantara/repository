# - coding: utf-8 -
#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#


"""
The layout of scan images on the filesystem is specified in this file.
It looks like this:
restrepo/files
└── original_scans
    └── 0-1000
        └── 1
"""

import os
import glob
import json
import types
import re
from PIL import Image
from StringIO import StringIO
from sqlalchemy import Table, Column, Unicode, Integer, String
from sqlalchemy import Date
from sqlalchemy.orm import object_session

from pyramid.threadlocal import get_current_registry

from watermarker import place_watermark

from restrepo.config import status as status_values
from restrepo.config import CACHE_SUBDIRECTORY
from restrepo.db import metadata
from restrepo.db.archive import get_archive
from restrepo.db.archive import get_archives
from restrepo.db.mixins import JsonSaver, DictAble
from restrepo.utils import datetime_to_string_zulu, datetime_to_string
from restrepo.storage import store_file, real_path
from restrepo.storage import file_exists, get_file_handle
from restrepo.db import UTCDateTime

scan = Table(
    'scan',
    metadata,
    Column('number', Integer, primary_key=True),
    Column('archive_id', Integer, index=True),
    Column('archiveFile', Unicode(255), index=True),
    Column('sequenceNumber', Integer, index=True),  # provides scan ordering
    Column('json_data', String),
    Column('status', Integer, default=status_values.NEW),
    Column('date', UTCDateTime(timezone=True), index=True),
    Column('timeFrameFrom', Date, index=True),
    Column('timeFrameTo', Date, index=True),
    Column('transcriptionDate', Date, index=True),
    Column('translationENDate', Date, index=True),
    Column('translationIDDate', Date, index=True),
    Column('last_modified', UTCDateTime(timezone=True)),
)


class Scan(JsonSaver, DictAble):
    def to_dict(self, request=None, dbdata_only=False, include_images=False):
        """
        Return a JSON-serializable dict representing this object.
        A request object is needed unless dbdata_only is True.

        TODO: the json_data thing HORRIBLE (because it is magic, and makes it completely untranspartent in the code or db structure
        which data we actually save) - we need to remove it...
        """
        me = dict(self)
        del me['json_data']
        me['dateLastModified'] = me['last_modified']
        del me['last_modified']
        if not dbdata_only:
            me['URL'] = request.route_url('service_scan_item', **me)
            if include_images:
                me['images'] = []
                for image in self.images:
                    imagedict = dict(
                        filename=image.filename, id=image.id,
                        url=request.route_url(
                            # SERVICE_SCAN_IMAGES_ITEM,
                            'service_scan_images_item',
                            number=self.number,
                            number_of_image=image.id
                        )
                    )
                    me['images'].append(imagedict)
        if self.json_data:
            me.update(json.loads(self.json_data))
        # ???
        if 'id' in me:
            del me['id']
        return me

    def store_file(self, filecontents, image_id):
        store_file(self.get_file_path(image_id), filecontents)

    def remove_file(self, image_id):
        dirpath = real_path(self._get_thumbnail_dir())
        if not os.path.isdir(dirpath):
            return  # No thumbnails generated yet, nothing to do here.
        for filename in os.listdir(dirpath):
            os.unlink(os.path.join(dirpath, filename))

    def delete_files(self):
        """delete all files belonging to this scan"""
        for image in self.images:
            self.delete_files_for_image(image.id)

    def delete_files_for_image(self, id):  # @ReservedAssignment
        fp = real_path(self.get_file_path(id))
        if os.path.exists(fp):
            os.remove(fp)
        fp = real_path(self._thumbnail_basepath(id))
        for fn in glob.glob(fp + '*'):
            os.remove(fn)

    def _thumbnail_basepath(self, image_id):
        # self.id = image_id
        return os.path.join(self._get_thumbnail_dir(), str(image_id))

    def get_file_path(self, image_id):
        "Return the (relative) path to the original image with id image_id"
        return os.path.sep.join([
            'original_scans',
            _get_archive_path(self.number),
            str(self.number),
            str(image_id)
        ])

    def get_real_path(self, image_id):
        return real_path(self.get_file_path(image_id))

    def _get_thumbnail_dir(self):
        return os.path.join(
            CACHE_SUBDIRECTORY,
            _get_archive_path(self.number),
            str(self.number),
        )

    def get_thumbnail_path(self, size, image_id):
        """
        Return a path to a resized version of the image identified by image_id

        if no resized version exists, it will be created

        if size is equal to None, or if size is larger than the original file

        size is a string of the form INTxINT

        where INT can be an integer string or an empty string
        """

        if size is None:
            pass
            # do not return the original image, because we need to watermark it
            # return self.get_file_path(image_id)
        elif re.match('[0-9]+$', size):
            size = 'x' + size  # is size is simply a giti, it is interpreted max height.
        elif re.match('([0-9]*)x([0-9]*)$', size) and size != 'x':
            pass
        else:
            raise ValueError("Size must be like 300x200 or x400 or 200x")

        basepath = self._thumbnail_basepath(image_id)
        thumbnail_path = "%s-%s" % (basepath, size)

        if not file_exists(thumbnail_path):
            fh = get_file_handle(self.get_file_path(image_id))
            img = Image.open(fh)
            if not size:
                size = '100000x10000'
            w, h = get_resized_size(size.split('x'), img.size)
            if w >= img.size[0]:
                # we asked for an image larger than the original - we return the original instead
                w, h = img.size
#                 return self.get_file_path(image_id)
            img.thumbnail((w, h), Image.ANTIALIAS)
            thumb_fh = StringIO()
            if img.mode == "P":
                img = img.convert("RGB")
            img.save(thumb_fh, 'JPEG', **img.info)
            thumb_fh.seek(0)

            # determine if we need to watermark this file
            settings = get_current_registry().settings
            if w > 100 and h > 100 and settings.get('watermark_file'):
                # place a watrmark
                save_fh = StringIO()
                watermark_fh = open(settings['watermark_file'])
                watermark_size_width = settings['watermark_size']
                pos_x = settings['watermark_pos_x']
                pos_y = settings['watermark_pos_y']
                if isinstance(pos_x, types.StringTypes) and pos_x.isdigit():
                    pos_x = int(pos_x)
                if isinstance(pos_y, types.StringTypes) and pos_y.isdigit():
                    pos_y = int(pos_y)
                image_format = settings['watermark_image_format']
                place_watermark(
                    thumb_fh,
                    save_fh,
                    watermark_file=watermark_fh,
                    filetype='img',
                    watermark_size_width=watermark_size_width,
                    pos_x=pos_x,
                    pos_y=pos_y,
                    image_format=image_format,
                )
            else:
                save_fh = thumb_fh

            store_file(thumbnail_path, save_fh.getvalue())
            thumb_fh.close()
            save_fh.close()
            fh.close()

        return thumbnail_path

    def get_real_thumbnail_path(self, size, image_id):
        return real_path(self.get_thumbnail_path(size, image_id))

    def get_solr_data(self, partial_update_keys=None):
        """return a dictionary that can be indexed by solr

            partial_update_keys is a list of keys
            if partial_update_keys is given, we compute only values that depend on these keys
            and return a dictionary with all values of the form {'set':value} (which instructs solr to do a partial document update)
            This can be used for optimizing updates
        """

        def maybe(date):
            if date:
                date = datetime_to_string_zulu(date)
            return date

        # we first calculate the cheap keys
        solr_data = dict(
            number=self.number,
            sequenceNumber=self.sequenceNumber,
            URI=getattr(self, 'URI', None),
            status=self.status,
            dateLastModified=datetime_to_string_zulu(self.last_modified),
            date=maybe(self.date),
            folioNumber=getattr(self, 'folioNumber', None),
            originalFolioNumber=getattr(self, 'originalFolioNumber', None),
            title=getattr(self, 'title', None),
            subjectEN=getattr(self, 'subjectEN', None),
            transcription=getattr(self, 'transcription', None),
            transcriptionAuthor=getattr(self, 'transcriptionAuthor', None),
            transcriptionDate=maybe(getattr(self, 'transcriptionDate', None)),
            translationEN=getattr(self, 'translationEN', None),
            translationENDate=maybe(getattr(self, 'translationENDate', None)),
            translationENAuthor=getattr(self, 'translationENAuthor', None),
            translationID=getattr(self, 'translationID', None),
            translationIDAuthor=getattr(self, 'translationIDAuthor', None),
            type=getattr(self, 'type', None),
            language=getattr(self, 'language', None),
            relation=getattr(self, 'relation', None),
            source=getattr(self, 'source', None),
            creator=getattr(self, 'creator', None),
            format=getattr(self, 'format', None),
            contributor=getattr(self, 'contributor', None),
            publisher=getattr(self, 'publisher', None),
            rights=getattr(self, 'rights', None),
            user=getattr(self, 'user', None),
            timeFrameFrom=datetime_to_string(self.timeFrameFrom),
            timeFrameTo=datetime_to_string(self.timeFrameTo),
            translationIDDate=maybe(self.translationIDDate),
            archiveFile=self.archiveFile,
            text=self.get_solr_text(),
        )
        if partial_update_keys:
            if 'archive_id' in partial_update_keys:
                solr_data.update(dict(
                    archive_id=self.archive_id,
                    archive=self.get_archive(),
                    country=self.get_country(),
                    institution=self.get_institution(),
                ))
            if 'file' in partial_update_keys:
                solr_data.update(dict(
                    default_image_id=self.get_default_image() and self.get_default_image().id,
                    images_ids=[image.id for image in self.images],
                    images_filenames=[image.filename for image in self.images],
                ))
            solr_data = dict([(k, {'set': solr_data[k]}) for k in solr_data])
            solr_data['number'] = solr_data['number']['set']
        else:
            # we calculate all the data
            solr_data.update(dict(
                archive_id=self.archive_id,
                archiveFile=self.archiveFile,
                archive=self.get_archive(),
                country=self.get_country(),
                institution=self.get_institution(),
                # The following three fields will be collapsed in an array
                # of dicts before being returned to the client.
                # collapse_images_array is the function responsible of the conversion.
                default_image_id=self.get_default_image() and self.get_default_image().id,
                images_ids=[image.id for image in self.images],
                images_filenames=[image.filename for image in self.images],
            ))

        return solr_data

    def get_default_image(self):
        ls = [image for image in self.images if image.is_default]
        if ls:
            return ls[0]

    def get_solr_text(self):
        "Put together some text for solr fulltext search (TODO)"
        # TODO: implement get_solr_text for searching in text of scans
        # use the SOLR index 'search_source' for this (just as ead_components do)
        return ''

    def get_country(self):
        archive = self.get_archive_data()
        return archive['country_code']

    def get_institution(self):
        "get institution from the archive linked to this scan"
        archive = self.get_archive_data()
        return archive['institution']

    def get_archive(self):
        "get archive from the archive linked to this scan"
        return self.get_archive_data()['archive']

    def get_archive_data(self):
        "get archive info linked to this scan"
        try:
            return self._archive_data
        except AttributeError:
            db = object_session(self)
            archive = get_archive(Context(db), archive_id=self.archive_id)
            if archive:
                self._archive_data = archive.to_dict()
        return self._archive_data


def _get_archive_path(number):
    """
    Returns the directory name where a scan images
    should be stored, based on its id.

    >>> _get_archive_path(30)
    '0-1000'
    >>> _get_archive_path(999)
    '0-1000'
    >>> _get_archive_path(1000)
    '1000-2000'
    >>> _get_archive_path(1001)
    '1000-2000'
    >>> _get_archive_path(1002)
    '1000-2000'
    """
    _id = number
    start = (_id / 1000) * 1000
    end = (_id / 1000 + 1) * 1000
    # We use directories with 1000 files max
    # and name them 0-1000, 1000-2000 etc
    return '%s-%s' % (start, end)


def collapse_images_array(scandata):
    """
    Collapse the three elements in a scan dict representing images
    to a single array of image dicts

    >>> data = {"default_image_id":2, "images_ids": [2,1,3], "images_filenames":["image2", "image1", "image3"]}
    >>> data['some_other_key'] = 'test'
    >>> result = collapse_images_array(data)
    >>> result['images']
    [{'is_default': True, 'id': 2, 'filename': 'image2'}, {'is_default': False, 'id': 1, 'filename': 'image1'}, {'is_default': False, 'id': 3, 'filename': 'image3'}]
    >>> result["some_other_key"]
    'test'
    >>> "images_ids" in result
    False
    >>> "images_filenames" in result
    False
    >>> "default_image_id" in result
    False
    """
    images = sorted([
        dict(filename=scandata['images_filenames'][i],
             id=id,
             is_default=(id == scandata.get("default_image_id")))
        for i, id in enumerate(scandata.get("images_ids", []))
    ], key=lambda x: (not x["is_default"], x['id']))
    result = dict(scandata)
    for k in "default_image_id", "images_ids", "images_filenames":
        if k in result:
            del result[k]
    result["images"] = images
    return result


class Context:
    def __init__(self, db):
        self.db = db


def get_resized_size(newsize, oldsize):
    """
    newsize and oldsize are pairs of the form (width, height)
    Given a target w and h return h, v so that their ratio is the same as
    oldwidth, oldheight. width and height can be strings (also empty).
    For example:

    >>> get_resized_size(('100', ''), (1, 1))
    (100, 100)
    >>> get_resized_size(('', '100'), (1, 1))
    (100, 100)
    >>> get_resized_size(('', '100'), (1, 2))
    (50, 100)
    """
    # If one of the parameters is missing calculate it using the ratio
    # from old values
    width, height = newsize
    oldwidth, oldheight = oldsize
    oldratio = oldwidth / float(oldheight)
    if not width:
        height = int(height)
        width = height * oldratio
    elif not height:
        width = int(width)
        height = width / oldratio
    return int(width), int(height)


def get_scans(context, **kwargs):
    return get_scans_query(context, **kwargs).all()


def get_scans_query(
    context,
    archive_id=None,
    archiveFile=None,
    order_by=None,
    order_dir=None,
    archive=None,
    institution=None,
    status=None,
):
    """returns a SQLAlchemy query

        order by is a list of column names.
            if prefixed with a '-', we sort descending

        order_dir is deprecated
    """
    db = context.db

    condition = (Scan.sequenceNumber != None)
    condition &= (Scan.status != status_values.DELETED)

    if archive_id:
        condition = (Scan.archive_id == archive_id) & condition
    if archiveFile:
        condition = (Scan.archiveFile == archiveFile) & condition

    if archive and institution:
        archives = get_archives(archive=archive, institution=institution)
    elif archive:
        archives = get_archives(archive=archive)
    elif institution:
        archives = get_archives(institution=institution)
    else:
        archives = None

    if archives is not None:
        archive_ids = [arch.id for arch in archives]
        condition &= (Scan.archive_id.in_(archive_ids))

    if status:
        condition &= (Scan.status == status)

    query = db.query(Scan).filter(condition)

    if order_by:
        for col_name in order_by:
            desc = False
            if col_name.startswith('-'):
                col_name = col_name[1:]
                desc = True
            order_by_clause = getattr(Scan, col_name)
            if order_dir == 'DESC' or desc:
                order_by_clause = order_by_clause.desc()
            query = query.order_by(order_by_clause)

    return query
