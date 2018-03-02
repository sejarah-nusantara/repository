#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#


import os
import csv
from lxml import etree

from sqlalchemy import Table, Column, Integer, String
from sqlalchemy.orm import mapper
from restrepo.config import status
from restrepo.db import metadata, UTCDateTime
from restrepo.db.archive import get_archives, get_archive
from restrepo.storage import get_file, store_file
from restrepo.utils import datetime_to_string_zulu
from restrepo.utils import now, string_to_datetime
from restrepo.config import FN_EAD2VIEWER_MAPPING

ead_file = Table(
    'ead_file',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(100), nullable=False, unique=True, index=True),
    Column('status', Integer, default=status.NEW),
    Column('last_modified', UTCDateTime(timezone=True)),
)

c_node_tags = ['c'] + ['c0%s' % i for i in range(1, 10)]
c_node_selector = '//*[%s]' % ' or '.join(['self::%s' % c for c in c_node_tags])


def _compute_ead2view():
    """return a list of objects that represent items in an EAD file"""
    headers = ['xpath', '_location', 'caption_en', 'caption_nl', 'caption_id', '_comment']
    reader = csv.reader(open(FN_EAD2VIEWER_MAPPING), delimiter='\t')

    class EadElementConfig(object):
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        @property
        def show_in_tree(self):
            return self._location == 'isNode'

    lines = [dict(zip(headers, l)) for l in reader]
    # skip the first line (these are headers)
    lines = lines[1:]
    lines = [l for l in lines if l['_location'] not in ['n.a.']]
    lines = [l for l in lines if l['xpath']]
    lines = [l for l in lines if not l['xpath'].startswith('/ead/archdesc/dsc/*/c')]
    return [EadElementConfig(**l) for l in lines]

# store the value at compile time
_ead2view = _compute_ead2view()


def ead2view():
    return _ead2view


def add_ead_file(
    context,
    name,
    filecontents,
    status=1,
    ):
    """Add an EAD file

    NB: No validation, No logging, use with care!
    (validation and loggging is done in browser.ead.service_add_ead_file)
    """
    eadfile = EadFile(context=context)
    eadfile.name = name
    eadfile.status = status
    store_file(eadfile.get_file_path(), filecontents,)
    context.db.add(eadfile)
    eadfile.last_modified = now()
    return eadfile


def get_ead_files(context):
    """return all EadFile objects in the database"""
    db = context.db
    result = db.query(EadFile).all()
    for el in result:
        el._context = context
    return result


def get_ead_file(context, ead_id):
    # XXX using ead_id externally and name internally can lead to confusion
    query = context.db.query(EadFile).filter(EadFile.name == ead_id)
    ead_file = query.one()
    ead_file._context = context
    return ead_file


class InvalidinstitutionException(Exception):
    def __str__(self):
        return """Invalid value for institution, or no value found.
(we looked for the attribute "repositorycode"  in /ead/archdesc/did/unitid)"""


def get_institution(xml_root):
    """return the identifier of the institution

    is in /did/unitid[@repository_code]
    """
    # xpath is relative to the root (= the 'ead' element)
    xpath = 'archdesc/did/unitid'
    unitid = xml_root.find(xpath)
    if unitid is None:
        raise InvalidinstitutionException()
    else:
        try:
            institution = unitid.attrib['repositorycode']
        except KeyError:
            raise InvalidinstitutionException()
    if not institution:
        raise InvalidinstitutionException()
    return institution


def get_title(xml_root):
    xpath = 'eadheader/filedesc/titlestmt/titleproper'
    el_title = xml_root.find(xpath)
    return el_title.text


class InvalidArchiveException(Exception):
    def __str__(self):
        return """Invalid value for archive, or no value found.
            (we looked for /ead/archdesc/did/unitid"""


def get_archive_from_xml(xml_root):
    """return the identifier of the archive"""
    # xpath is relative to the root (= the 'ead' element)
    xpath = 'archdesc/did/unitid'
    unitid = xml_root.find(xpath)
    if unitid is None:
        raise InvalidArchiveException()
    else:
        archive = unitid.text
    if not archive:
        raise InvalidArchiveException()
    return archive


class EadFile(object):

    def __init__(self, context=None, **kwargs):
        self._context = context
        if kwargs:
            self.name = kwargs['ead_id']
        for key, value in kwargs.items():
            if key in ['dateLastModified']:
                value = string_to_datetime(value)
                key = 'last_modified'
            setattr(self, key, value)

    def to_dict(self, request=None, dbdata_only=False):
        """
        Return a dict representing this object.
        A request object is needed unless dbdata_only is True.
        """
        me = dict(
            status=self.status,
            dateLastModified=self.dateLastModified,
        )

        me.update(self.get_solr_data())
        if not dbdata_only:
            me['URL'] = request.route_url('ead_file', **me)
            
        archives = get_archives(
            self._context,
            institution=me['institution'],
            archive=me['archive'],
        )

        if archives:
            assert len(archives) == 1
            me['archive_id'] = archives[0].id
        else:
            me['archive_id'] = None

        me['title'] = self.get_title()
        return me

    def get_solr_data(self):
        solr_data = {
            'archive': self.get_archive(),
            'archive_id': self.get_archive_id(),
            'country': self.get_country(),
            'dateLastModified': self.dateLastModified,
            'ead_id': self.name,
            'findingaid': self.get_findingaid(),
            'institution': self.get_institution(),
            'language': self.get_language(),
            'status': self.status,
        }
        return solr_data

    def get_file_path(self):
        return os.path.sep.join(['ead_files', str(self.name)])

    def _get_xml_tree(self):
        # TODO: OPTIMIZATION: this is expensive: either cache this, or don't call it often (at the moment is is called often)
        self._tree = etree.parse(get_file(self.get_file_path()))
        return self._tree

    @property
    def _cache(self):
        """somewhat of a hack to have quick access to calculated values
        without having to do all kinds of cache invalidation
        """
        try:
            return self._cached_data
        except AttributeError:
            self._cached_data = self.get_solr_data()
            return self._cached_data

    @property
    def dateLastModified(self):
        return datetime_to_string_zulu(self.last_modified)

    def extract_components(self):
        """return all component elements from the EAD file that can be visualized

        these are either:
            1. c_nodes, OR
            2. elements that have text and that are explicitly mentioned in config.FN_EAD2VIEWER_MAPPING

        elements are returned in the order that they appear in the document.

        this is the function that is used for filling the solr index
        """
        from restrepo.db.eadcomponent import EadComponent, EadTextElement
        root = self._get_xml_tree().getroot()

        result = []
        #
        # get all predifined nodes
        #
        prev_component = None

        langcode = self.get_language()

        for i, l in enumerate(ead2view()):
            title = getattr(l, 'caption_%s' % langcode)
            text_lines = root.xpath(l.xpath)
            component = EadTextElement(
                title=title,
                text_lines=text_lines,
                xpath=l.xpath, ead_file=self,
                context=self._context,
                prev=prev_component,
                show_in_tree=l.show_in_tree,
                sequenceNumber=i,
                )
            result.append(component)
            prev_component = component

        #
        # get all c-elements
        #
        offset = i  # we already added i documents, so we need our sequenceNumber to start afterwards
        components = root.xpath(c_node_selector)
        prev_component = None
        for i, el_component in enumerate(components):
            component = EadComponent(
                element=el_component,
                ead_file=self,
                prev=prev_component,
                context=self._context,
                sequenceNumber=i + offset,
                )
            result.append(component)
            prev_component = component

        return result

    def extract_component_dicts(self):
        """extract component JSON data for indexing"""
        return [component.get_solr_data() for component in self.extract_components()]

    def get_archive_file_ids(self):
        """return all identifiers of archiveFile elements in this EAD file"""
        return [c.archiveFile for c in self.extract_components() if c.archiveFile]

    def get_archive(self):
        return get_archive_from_xml(self._get_xml_tree().getroot())

    def get_country(self):
        xpath = 'eadheader/eadid'
        xml_root = self._get_xml_tree().getroot()
        return xml_root.find(xpath).attrib.get('countrycode', None)

    def get_findingaid(self):
        xpath = 'eadheader/eadid'
        xml_root = self._get_xml_tree().getroot()
        return xml_root.find(xpath).text

    def get_institution(self):
        return get_institution(self._get_xml_tree().getroot())

    def get_title(self):
        return get_title(self._get_xml_tree().getroot())

    def get_archive_id(self):

        archive = get_archive(
            self._context,
            institution=self.get_institution(),
            archive=self.get_archive(),
            )
        return archive.id

    def get_language(self):
#         """return one of 'id', 'en' or 'nl', default is 'en'"""
        xpath = 'eadheader/profiledesc/langusage/language'
        el_language = self._get_xml_tree().find(xpath)

        mapping = {
            'ind': 'id',
            'id': 'id',
            'eng': 'en',
            'en': 'en',
            'ned': 'nl',
            'dut': 'nl',
            'nl': 'nl',
        }

        if el_language is not None:
            langcode = el_language.attrib['langcode']
            try:
                return mapping[langcode]
            except:
                raise Exception('Unknow language encoding "%s" in file %s' % (langcode, self.name))
        else:
            return 'en'


mapper(EadFile, ead_file)
