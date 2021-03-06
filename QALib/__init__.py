import os
import sys

__slicer_module__ = os.path.dirname(os.path.abspath(__path__[0]))
# print "Path to module: %s" % __slicer_module__

try:
    import pg8000
except ImportError:
    pg8kDir = [os.path.join(__slicer_module__, 'Resources', 'Python', 'pg8000-1.08')]
    newSysPath = pg8kDir + sys.path
    sys.path = newSysPath
    import pg8000

sql = pg8000.DBAPI
