"""Services to be consumed by the pagebrowser"""
from lxml import etree
import colander
from cornice import Service

from restrepo.models.utils import el
from restrepo.config import SERVICE_PAGEBROWSER_PAGELIST, STATUS_PUBLISHED
from restrepo.browser.validation import validate_schema
# from restrepo.db.scans import get_scans
from restrepo import solr
from restrepo.solr import scans # need this to get 'scans' in the solr namespace


service_pagelist = Service(
    name='bookservicepagelist',
    path=SERVICE_PAGEBROWSER_PAGELIST,
    description=__doc__,
    renderer='string',
)


class PageListSchema(colander.MappingSchema):
    archive_id = el('int', required=True)
    archiveFile = el('string', required=True)


def valid_pagelist_arguments(request):
    "Check incoming data: ensure desired schema"
    schema = PageListSchema()
    validate_schema(schema, request.matchdict, request)


@service_pagelist.get(validators=[valid_pagelist_arguments])
def pagelist(request):
    """return an xml file with a information about a list of pages

        s += '<?xml version="1.0" encoding="%s"?>\n' % self.encoding
        s += '<bookservice>\n'
        s += '<meta pdf_download_file_exists="%s">\n' % \
            self._whole_book_fn_exists()
        s += '</meta>\n'
        s += '<pagelist>\n'
        for p in self.getPages():
        s = ''
        s += '\t <page \n'
        s += '\t\tid="%s"\n' % self.id
        s += '\t\timage="%s"\n' % self.image_url
        s += '\t\tpdf="%s"\n' % self.pdf_url
        s += '\t\tfn_pdf="%s"\n' % self.fn_pdf
        s += '\t\thtml="%s"\n' % self.html_url
        s += '\t\tthumb="%s"\n' % self.thumb_url
        s += '\t\tpage_number="%s"\n' % self.page_number
        s += '\t\tpage_index="%s"\n' % self.page_index
        s += '\t/>
        s += '</pagelist>'
        s += '</bookservice>'
    """
    root = etree.Element('bookservice')
    el_meta = etree.Element('meta')
    el_meta.attrib['pdf_download_file_exists'] = 'False'
    root.append(el_meta)
    el_pagelist = etree.Element('pagelist')

    # scans = get_scans(request, status=STATUS_PUBLISHED, order_by=['sequenceNumber'], **request.validated)
    solr_query, order_by = solr.scans.create_query(status=STATUS_PUBLISHED, order_by=['sequenceNumber'], **request.validated)

    result = request.solr_scan.search(q=solr_query, sort=order_by, rows=10000)

    for i, scan in enumerate(result.documents):
        d = scan
        el_page = etree.Element('page')
        el_page.attrib['id'] = unicode(d['number'])
        URL = request.route_url('service_scan_item', number=d['number'])
        el_page.attrib['image'] = URL + '/image'
        el_page.attrib['thumb'] = URL + '/image?size=x200'
        el_page.attrib['page_number'] = unicode(d.get('folioNumber') or d.get('sequenceNumber') or '')
        el_page.attrib['page_index'] = unicode(i)
        el_page.attrib['timeFrameFrom'] = unicode(d.get('timeFrameFrom', ''))
        el_page.attrib['timeFrameTo'] = unicode(d.get('timeFrameTo', ''))
        el_pagelist.append(el_page)
    root.append(el_pagelist)
    request.response_content_type = 'text/xml'

    return etree.tostring(
        root,
        encoding='UTF-8',
    )
