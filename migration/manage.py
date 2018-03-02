#!/usr/bin/env python
"""This is a command utility to migrate (upgrade) restrepo database

"""
from migrate.versioning.shell import main

if __name__ == '__main__':
    raise Exception('Use manage.py in ..')
    main(url='postgresql:///restrepo_staging', debug='False', repository='migration')