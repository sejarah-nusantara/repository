import logging

from restrepo.db.scans import get_scans
from restrepo.db.ead import get_ead_files
from restrepo.db.ead import EadFile
from restrepo.indexes.archivefile import cast_component_as_archivefile, cast_scan_as_archivefile
from restrepo.db.archivefile import get_archivefiles

logger = logging.getLogger(__name__)


def reindex_all(context, delete=True):
    print 'deleting all'
    if delete:
        context.solr.delete_by_query('*:*')
    print 'reindexing ead files'
    reindex_ead_files(context, delete=delete)
    print 'reindexing components'
    reindex_components(context, delete=delete)
    print 'reindexing archive files'
    reindex_archivefiles(context, delete=delete)
    print 'reindexing scans files'
    reindex_scans(context, delete=delete)
    print 'reindexing archive files again'
    reindex_archivefiles(context, delete=delete)


def reindex_ead_files(context, delete=True):
    # reindex ead files
    if delete:
        logger.debug('deleted all eads from index')
    context.solr_ead.delete_by_query('*:*')
    documents = [doc.get_solr_data() for doc in get_ead_files(context)]
    logger.debug('indexing {} documents'.format(len(documents)))
    context.solr_ead.update(documents)
    context.solr_ead.commit()  # soft_commit=False)


def reindex_scans(context, delete=True):
    # reindex scans
    logger.debug('deleting existing scans from index')
    if delete:
        context.solr_scan.delete_by_query('*:*')
    documents = get_scans(context)
    batch_size = 1000
    logger.debug('scans to index:', len(documents))
    for i in range(len(documents) / batch_size + 1):
        start = i * batch_size
        end = (i + 1) * batch_size
        number = len(documents[start:end])
        logger.debug('indexing scans {start} to {end} ({number} docs)'.format(**locals()))
        documents_to_index = [scan.get_solr_data() for scan in documents[start:end]]
        context.solr_scan.update(documents_to_index)
        context.solr_scan.commit()  # soft_commit=True)


def get_ead_components(context, delete=True):
    """get all ead components from all ead files """
    result = []
    for ead_file in context.db.query(EadFile):
        ead_file._context = context
        result += ead_file.extract_components()
    return result


def reindex_components(context, delete=True):
    # reindex components
    if delete:
        context.solr_eadcomponent.delete_by_query('*:*')
    documents = [component.get_solr_data() for component in get_ead_components(context)]
    context.solr_eadcomponent.update(documents)
    context.solr_eadcomponent.commit()  # soft_commit=True)


def reindex_archivefiles(context, delete=True):
    logger.debug('deleting archive files from index..')
    if delete:
        context.solr_archivefile.delete_by_query('*:*')

    logger.debug('collecting data to index...')
    documents = [component.get_solr_data() for component in get_ead_components(context)]
    documents = [cast_component_as_archivefile(component).get_solr_data(context) for component in documents if component['is_archiveFile']]
    logger.debug('documents to index (components) ', len(documents))
    context.solr_archivefile.update(documents)
    context.solr_archivefile.commit()

    # get the scans from the database
    logger.debug('collecting data to index...')
    already_indexed = [(x['archive_id'], x['archiveFile']) for x in documents]
    scans = get_scans(context)
    scans = [scan for scan in scans if (scan.archive_id, scan.archiveFile) not in already_indexed]
    documents = [cast_scan_as_archivefile(context, scan.get_solr_data()).get_solr_data(context) for scan in scans]
    logger.debug('documents to index (from scans) ', len(documents))
    context.solr_archivefile.update(documents)
    context.solr_archivefile.commit()

    from restrepo.db.archivefile import get_archivefiles
    # archivefiles from db
    logger.debug('collecting data to index...')
    documents = get_archivefiles(context)
    documents = [x.get_solr_data(context) for x in documents]
    logger.debug('documents to index (from db) ', len(documents))
    context.solr_archivefile.update(documents)

    context.solr_archivefile.commit()


def refresh_archivefiles(context, delete=True):
    if delete:
        context.solr_archivefile.delete_by_query('*:*')

    documents = [component.get_solr_data() for component in get_ead_components(context)]
    documents = [cast_component_as_archivefile(component).get_solr_data(context) for component in documents if component['is_archiveFile']]
    context.solr_archivefile.update(documents)
    context.solr_archivefile.commit()

    # get the scans from the database
    already_indexed = [(x['archive_id'], x['archiveFile']) for x in documents]
    scans = get_scans(context)
    scans = [scan for scan in scans if (scan.archive_id, scan.archiveFile) not in already_indexed]
    documents = [cast_scan_as_archivefile(context, scan.get_solr_data()).get_solr_data(context) for scan in scans]
    context.solr_archivefile.update(documents)
    context.solr_archivefile.commit()

    # archivefiles from db
    documents = get_archivefiles(context)
    documents = [x.get_solr_data(context) for x in documents]
    context.solr_archivefile.update(documents)

    context.solr_archivefile.commit()
