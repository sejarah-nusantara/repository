from restrepo.solr import build_equality_query


def create_query(
    archive_id=None,
    archiveFile=None,
    order_by=None,
    order_dir=None,
    archive=None,
    institution=None,
    status=None,
):

    solr_query = build_equality_query(
        archiveFile=archiveFile,
        archive=archive,
        archive_id=archive_id,
        status=status,
        institution=institution,
    )

    # order_dir is implemented but deprecated:
    # we can pass -colname in order_by to sort desc.
    # start = request.validated['start']
    # limit = request.validated['limit']
    order_by_clause = []
    for fieldname in order_by:
        desc = fieldname.startswith('-')
        if desc:
            fieldname = fieldname[1:]
        if not desc:
            order_by_clause.append('%s asc' % fieldname)
        else:
            order_by_clause.append('%s desc' % fieldname)
    order_by_clause = ','.join(order_by_clause)

    return (solr_query, order_by_clause)
