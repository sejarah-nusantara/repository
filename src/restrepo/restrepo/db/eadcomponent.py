import json
import datetime
from restrepo.utils import flatten, string_to_datetime, datetime_to_string_zulu
from restrepo.utils import cleanup_string, content_tostring
from restrepo.db.mixins import DictAble
from restrepo.db.ead import c_node_selector
from restrepo.db.solr import build_equality_query
from restrepo.db.archivefile import get_archivefile
from restrepo import config


def get_archive_file_ids(xml_root):
    xpath = '%s[@level="file"]/did/unitid' % c_node_selector
    return [x.text for x in xml_root.xpath(xpath)]


class EadTextElement(DictAble):
    """This is an element of an EAD file.
    """
    def __init__(
        self,
        title,
        text_lines,
        xpath,
        ead_file,
        context,
        sequenceNumber,
        prev=None,
        show_in_tree=True,
        ):
        self.is_component = False
        self.title = title
        self.xpath = xpath
        self._text_lines = text_lines
        self._ead_file = ead_file
        self._context = context
        self.sequenceNumber = sequenceNumber
        self.archive = ead_file._cache['archive']
        self.archive_id = ead_file._cache['archive_id']
        self.country = ead_file._cache['country']
        self.ead_id = ead_file._cache['ead_id']
        self.institution = ead_file._cache['institution']
        self._text_lines = text_lines
        self.prev = prev
        self.next = None
        self.number_of_scans = 0
        if self.prev:
            self.prev.next = self
        self.show_in_tree = show_in_tree
        self.status = self.get_status(context)

    @classmethod
    def _field_names(cls):
        # these attributes will be indexed by SOLR
        return [
            'archive',
            'archive_id',
            'archiveFile',
            'breadcrumbs',
            'country',
            'custodhist',
            'date',
            'date_from',
            'date_to',
            'description',
            'ead_id',
            'eadcomponent_id',
            'findingaid',
            'institution',
            'is_archiveFile',
            'is_component',
            'level',
            'language',
            'number_of_scans',
            'parent',
            'scopecontent',
#             'sequenceNumber',
            'show_in_tree',
            'status',
            'search_source',
            'text',
            'title',
            'xpath',
            ]

    def get_solr_data(self):
        """returns a dictionary that is to be indexed by SOLR"""
        data = {}
        for k in self._field_names():
            v = getattr(self, k, None)
            if isinstance(v, datetime.datetime) or \
               isinstance(v, datetime.date):
                data[k] = datetime_to_string_zulu(v)
            else:
                data[k] = v
            # only add 'sequenceNumber' if we have calculated it (this allows us to update separate components without recalculating the index)
            if getattr(self, 'sequenceNumber', None) is not None:
                data['sequenceNumber'] = self.sequenceNumber
        return data

    def _xpath_contained_in(self, xpath, parent_xpath):
        if parent_xpath.endswith('[1]'):
            parent_xpath = parent_xpath[:-len('[1]')]
        if '/@' in parent_xpath:
            parent_xpath = parent_xpath.split('/@')[0]
        if parent_xpath.endswith('/text()'):
            parent_xpath = parent_xpath[:-(len('/text()'))]
        return xpath.startswith(parent_xpath) and len(parent_xpath) < len(xpath)

    @property
    def parent(self):
        """return id of parent"""
        parent = self.get_parent()
        if parent:
            return parent.eadcomponent_id

    def get_parent(self):
        """return the 'parent', which for text nodes is the first previous sibling that has 'show_in_tree' True"""
        if self.show_in_tree:
            return None
        node = self.prev
        while node:
            if node.show_in_tree:
                return node
            node = node.prev

    @property
    def text_lines(self):
        return self._text_lines

    @property
    def text(self):
        return [l.strip() for l in self.text_lines]

    @property
    def eadcomponent_id(self):
        return '%s/%s' % (self.ead_id, self.xpath)

    @property
    def is_rootlevel(self):
        return self.parent is None

    @property
    def search_source(self):
        return ' '.join(self.text_lines)

    # XXX: breadcrumbs seems to not be used anymore
    @property
    def breadcrumbs(self):
        current_node = self.get_parent()
        breadcrumbs = []
        while current_node:
            if current_node.show_in_tree:
                breadcrumbs.append(current_node)
            current_node = current_node.get_parent()

        breadcrumbs = [[x.xpath, x.title] for x in breadcrumbs]
        return unicode(json.dumps(breadcrumbs))

    def get_status(self, context=None):
        return config.STATUS_NEW


class EadComponent(EadTextElement):
    """A c-node in an ead-file"""

    def __init__(
        self,
        element,
        ead_file,
        prev,
        sequenceNumber,
        context=None,
        ):
        """
        element is a c-node within ead_file

        """
        self._element = element
        self.xpath = self._element.getroottree().getpath(self._element)
        self.next = None
        self.level = self._element.attrib.get('level', None)
        self.prev = prev
        EadTextElement.__init__(
            self,
            title=self.get_title(),
            text_lines=[],
            xpath=self.xpath,
            ead_file=ead_file,
            context=context,
            show_in_tree=self._show_in_tree(),
            prev=prev,
            sequenceNumber=sequenceNumber,
            )

        self.is_component = True
        self.number_of_scans = self.get_number_of_scans(context)

    def _show_in_tree(self):
        if not self.get_parent():
            return True
        if self.is_archiveFile:
            return False
        if self.get_parent().show_in_tree is False:
            return False
        return True

    def has_children(self):
        node = self.next

        if node and self._xpath_contained_in(node.xpath, self.xpath):
            return True

    def _xpath_contained_in(self, xpath, parent_xpath):
        return xpath.startswith(parent_xpath) and len(parent_xpath) < len(xpath)

    def get_parent(self):
        node = self.prev
        while node:
            if self._xpath_contained_in(self.xpath, node.xpath):
                return node
            node = node.prev

    @property
    def search_source(self):
        # this is the basis for full-text search, and also for the snippets
        result = []
        s = getattr(self, 'archiveFile')
        if s:
            result += [s + ' - ']
        attributes = [
            'title',
            'description',
            'scopecontent',
            ]
        result += [getattr(self, att, '') or '' for att in attributes]
        result += self.text
        result = ' '.join(result)
        result = cleanup_string(result)
        return result

    @property
    def date(self):
        """return the text content of did/unitdate"""
        el = self._element.find('did/unitdate')
        if el is not None:
            return el.text
        else:
            return el

    def _date_range(self):
        el = self._element.find('did/unitdate')
        if el is not None:
            datestring = el.attrib.get('normal', '')
            if '/' in datestring:
                date_from, date_to = datestring.split('/')
            else:
                date_from = datestring
                date_to = ''
            try:
                date_from = string_to_datetime(date_from)
            except:
                date_from = None
            try:
                date_to = string_to_datetime(
                    date_to,
                    default=datetime.datetime(2000, 12, 31),
                    )
            except:
                date_to = None
            return date_from, date_to
        else:
            return (None, None)

    @property
    def date_from(self):
        return self._date_range()[0]

    @property
    def date_to(self):
        return self._date_range()[1]

    @property
    def findingaid(self):
        return self._ead_file._cache['findingaid']

    @property
    def description(self):
        el = self._element.find('did/physdesc')
        if el is not None:
            return flatten(el)
        else:
            return ''

    @property
    def language(self):
        return self._ead_file._cache['language']

    @property
    def scopecontent(self):
        el = self._element.find('scopecontent')
        if el is not None:
            return content_tostring(el)
        else:
            return ''

    @property
    def custodhist(self):
        el = self._element.find('custodhist')
        if el is not None:
            return content_tostring(el)
        else:
            return ''

    def get_title(self):
        el_title = self._element.find('did/unittitle')
        if el_title is not None:
            return el_title.text
        else:
            return ''

    @property
    def is_archiveFile(self):
        return self.level == 'file'

    @property
    def archiveFile(self):
        if self.is_archiveFile:
            s = self._element.find('did/unitid').text
            if s != None:
                return unicode(s)
        else:
            return None

    @property
    def text_lines(self):
        return [self._element.text or '']

    def get_number_of_scans(self, context):
        #
        # cf also db.archivefile.ArchiveFile.number_of_scans
        #
        if self.is_archiveFile:
            solr_query = build_equality_query(
                archiveFile=self.archiveFile,
                archive_id=self.archive_id,
                )
            result = context.solr_scan.search(q=solr_query, rows=1)
            return result.total_results
        else:
            return 0

    def get_status(self, context):
        if self.is_archiveFile:
            # get the archivefile from the db (this is relatively expensive...)
            archivefile = get_archivefile(context, archive_id=self.archive_id, archiveFile=self.archiveFile)
            if archivefile:
                return archivefile.status
            else:
                return config.STATUS_NEW
        else:
            return config.STATUS_NEW
