#
# functions that assist in storing files on the filesystem
#

import os
from restrepo import REPO


def real_path(filepath, create=True):
    "return the real os path from a repo file path"
    if filepath.startswith('/'):
        raise ValueError("Use relative paths for repo files")
    dirname, filename = os.path.split(filepath)
    dirpath = os.path.join(REPO, dirname)
    if create and not os.path.isdir(dirpath):
        os.makedirs(dirpath)
    return os.path.join(dirpath, filename)


def store_file(filepath, filecontents):
    "filecontents is a string with the contents of the file"
    realpath = real_path(filepath)
    with open(realpath, 'w') as fh:
        fh.write(filecontents)


def get_file_handle(filepath):
    return open(real_path(filepath))


def get_file(filepath):
    "Retrieve file"
    realpath = real_path(filepath)
    return open(realpath)


def get_file_content(filepath):
    "Retrieve file content"
    return get_file(filepath).read()


def move_file(oldpath, newpath):
    "Change a file path"
    real_oldpath = real_path(oldpath)
    real_newpath = real_path(newpath)
    os.rename(real_oldpath, real_newpath)


def delete_file(filepath):
    "Remove a file"
    realpath = real_path(filepath, create=False)
    if not os.path.isfile(realpath):
        raise ValueError("'%s' not found" % filepath)
    # Housekeeping: clean empty directories XXX TODO
    os.unlink(realpath)


def file_exists(filepath):
    realpath = real_path(filepath, create=False)
    return os.path.isfile(realpath)
