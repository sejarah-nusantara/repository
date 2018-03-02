

def get_ead_files(context, **kwargs):
    """
    search in the solr index for ead files

    returns:
        EadFile instances
    """

    # TODO: next line may be absolete (we should be actually deleing files now)
    querylist = ['-status:0']
    for fieldname, value in kwargs.items():
        if value:
            querylist.append('+%s:%s' % (fieldname, value))
    results = context.solr_ead.search(q=' '.join(querylist)).documents
    return results
