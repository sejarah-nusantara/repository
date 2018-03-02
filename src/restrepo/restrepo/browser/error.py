# encoding=utf8
#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#

from cornice import Service

from restrepo import config

service_error = Service(name='service_error', path=config.SERVICE_ERROR)


@service_error.get(permission='write',)
def raise_error(request):
    """
    raise an error
    """  # The last line in the docstring is needed to avoid a sphynx warning
    # lock the whole scan table before calculating the next number
    raise Exception('This is a test error message, and is not something you should worry about')
