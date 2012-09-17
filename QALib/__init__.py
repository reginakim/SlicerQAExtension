import os
import sys

#import module_locator
#currentPath = module_locator.module_path()
#fullPath = os.path.abspath(currentPath)
#__file__, libPath = os.path.split(currentPath)
#print "File at QALib: %s" % __file__
#del currentPath, fullPath, libPath
# globals[]('__file__') = __file__
__slicer_module__ = os.path.sep.join(__path__[0].split(os.path.sep)[0:-1])
print "Path to module: %s" % __slicer_module__

try:
    import pg8000
except ImportError:
    print "pg8000 hack initiated..."
    ### Hack to import pg8000 locally
    pg8kDir = [os.path.join(__slicer_module__, 'Resources', 'Python', 'pg8000-1.08')]
    newSysPath = pg8kDir + sys.path
    sys.path = newSysPath
    import pg8000

sql = pg8000.DBAPI
# globals()['sql'] = pg8000.DBAPI
# globals()['pg8000'] = pg8000

