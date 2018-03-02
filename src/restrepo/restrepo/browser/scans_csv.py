# encoding=utf8
#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2014
#

""" Web service for download scans as a CSV file
"""

import json
import types
import StringIO
import csv

from cornice import Service

from restrepo import config
from restrepo.db.scans import collapse_images_array
from restrepo.db.solr import build_equality_query
from restrepo.utils import set_cors

from scans import valid_search_data


class CSVRenderer(object):
    def __init__(self, info):
        pass

    def __call__(self, value, system):
        fout = StringIO.StringIO()
        writer = csv.writer(fout, delimiter=',', quoting=csv.QUOTE_ALL)

        writer.writerow(value['header'])
        for row in value['rows']:
            writer.writerow([unicode(s).encode("utf-8") for s in row])
        # writer.writerows(value['rows'])

        resp = system['request'].response
        resp.content_type = 'text/csv'
        resp.content_disposition = 'attachment;filename="scans.csv"'
        return fout.getvalue()


service_scan_collection_csv = Service(
    name='service_scan_collection_csv',
    path=config.SERVICE_SCAN_COLLECTION_CSV,
    description=__doc__,
    renderer='csv')


@service_scan_collection_csv.get(validators=(valid_search_data), filters=set_cors)
def search_scans(request):
    """
    Search scans.


    parameters:
        %(PARAM_ARCHIVE_ID)s
        * **country:**
            the country of the scan (cf. %(SERVICE_ARCHIVE_COLLECTION)s)
        * **institution:**
            the institution of the scan (cf. %(SERVICE_ARCHIVE_COLLECTION)s)
        * **archive:**
            the archive of the scan (cf. %(SERVICE_ARCHIVE_COLLECTION)s)
        * **archiveFile:**
            the archiveFile of the scan
        * **archiveFile_raw:**
            an advanced option to search for ranges of archiveFile, using the solr syntax.
            For example, valid arguments are [1000 TO 2000] or [a OR b]
        * **timeFrame**
            return scans that have timeFrameFrom and timeFrameTo in this range
        * **folioNumber** (a string)
            search for scans with this folioNumber
        * **folioNumbers** a list of strings, of the form ["1", "xxx", "345"]
        * **originalFolioNumber** (a string)
            search for scans with this originalFolioNumber
        * **start:**
            index of the first element returned (used in pagination)
        * **limit:**
            max # of objects to return
        * **order_by:**
            a comma-separated list of field names to sort results on.
            Default order is by ``archive_id,archiveFile,sequenceNumber``.
            To sort descending, append '-' to a field name.
        * **status:**
            a status: a value among :ref:`status_values` (defaults to non-0)

        :returns:
            a csv-file with all data

    """
    # TODO: refactor: user restrepo.solr.scans.create_query
    solr_query = build_equality_query(
        archiveFile=request.validated['archiveFile'],
        archive=request.validated['archive'],
        archive_id=request.validated['archive_id'],
        status=request.validated['status'],
        institution=request.validated['institution'],
        date=request.validated['date'],
        folioNumber=request.validated['folioNumber'],
        originalFolioNumber=request.validated['originalFolioNumber'],
    )

    if request.validated['archiveFile_raw']:
        solr_query = ' AND '.join([solr_query, 'archiveFile:{}'.format(request.validated['archiveFile_raw'])])

    if request.validated['timeFrame']:
        solr_query += ' AND timeFrameFrom:[* TO %(timeFrame)s] AND timeFrameTo:[%(timeFrame)s TO *]' % request.validated

    if request.validated['folioNumbers']:
        folio_numbers = json.loads(request.validated['folioNumbers'])
        solr_query += ' AND (%s)' % ' OR '.join(['folioNumber:%s' % number for number in folio_numbers])

    # order_dir is implemented but deprecated:
    # we can pass -colname in order_by to sort desc.
    order_dir = request.validated['order_dir']
    start = request.validated['start']
    limit = request.validated['limit']
    order_by = []
    for fieldname in request.validated['order_by']:
        desc = fieldname.startswith('-')
        if desc:
            fieldname = fieldname[1:]
        # order_dir defaults to 'ASC'
        # order_dir = 'DESC' reverses the meaning of -
        # I know, awful, but if I need to support both APIs...
        if not desc and order_dir.lower() == 'asc':
            order_by.append('%s asc' % fieldname)
        else:
            order_by.append('%s desc' % fieldname)

    result = request.solr_scan.search(q=solr_query, sort=','.join(order_by), start=start, rows=limit)

    headers = [
        ('number', 'Number'),
        ('sequenceNumber', 'Sequence number'),
        ('filename', 'Original filename'),
        ('image_url', 'URL of image'),
        ('url', 'URL of scandata'),
        ('status', 'Status'),
        ('dateLastModified', 'Last modified'),
        ('institution', 'institution'),
        ('country', 'Country'),
        ('archive', 'archive'),
        ('archive_id', 'Archive id'),
        ('archiveFile', 'Archive File'),
        ('type', 'type'),
        ('language', 'language'),
        ('date', 'Date'),
        ('URI', 'URI'),
        ('folioNumber', 'Folio Number'),
        ('originalFolioNumber', 'Original Folio Number'),
        ('title', 'Title'),
        ('subjectEN', 'Subject (EN)'),
        ('transcription', 'Transcription'),
        ('transcriptionAuthor', 'Author of transcription'),
        ('transcriptionDate', 'Transcription date'),
        ('translationEN', 'Translation [EN]'),
        ('translationENDate', 'Translation date [EN]'),
        ('translationENAuthor', 'Translation author [EN]'),
        ('translationID', 'Translation [ID]'),
        ('translationIDAuthor', 'Translation author [ID]'),
        ('translationIDDate', 'Translation date [ID]'),
        ('relation', 'relation'),
        ('source', 'source'),
        ('creator', 'creator'),
        ('format', 'format'),
        ('contributor', 'contributor'),
        ('publisher', 'publisher'),
        ('rights', 'rights'),
        ('user', 'user'),
        ('timeFrameFrom', 'Time frame from'),
        ('timeFrameTo', 'Time frame to'),
    ]
    rows = []

    for doc in result.documents:
        default_image = collapse_images_array(doc)['images'][0]
        image_url = request.route_url(
            'service_scan_images_item',
            number=doc['number'],
            number_of_image=default_image["id"])
        doc['image_url'] = image_url
        url = request.route_url(
            'service_scan_item',
            number=doc['number']
        )
        doc['url'] = url
        doc['filename'] = default_image.get('filename')

        row = []
        for key, _head in headers:
            value = doc.get(key)
            row.append(value)
        rows.append(row)

    header = [head for _key, head in headers]

    return {
        'header': header,
        'rows': rows,
    }
