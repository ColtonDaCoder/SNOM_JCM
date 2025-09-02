import os


def smartpath(path, parent = None):
    if parent is None: parent = os.getcwd()

    if not os.path.isabs(path):
        path = os.path.join(parent, path)
    abspath = os.path.abspath(path)
    relpath = os.path.relpath(abspath, parent)

    if len(relpath)<len(abspath): return relpath
    else: return abspath
