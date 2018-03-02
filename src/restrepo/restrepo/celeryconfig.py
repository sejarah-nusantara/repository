
CELERY_ACCEPT_CONTENT = ['json', 'pickle']
CELERY_RESULT_BACKEND = 'amqp'

# If set to True, result messages will be persistent. This means the messages will not be lost after a broker restart. 
# The default is for the results to be transient.

CELERY_RESULT_PERSISTENT = False

# The number of concurrent worker processes/threads/green threads executing tasks.
CELERYD_CONCURRENCY = 1


# The global default rate limit for tasks.
# This value is used for tasks that does not have a custom rate limit The default is no rate limit.
# CELERY_DEFAULT_RATE_LIMIT


# By default any previously configured handlers on the root logger will be removed. If you want to customize
# your own logging handlers, then you can disable this behavior by setting CELERYD_HIJACK_ROOT_LOGGER = False.
CELERYD_HIJACK_ROOT_LOGGER = True