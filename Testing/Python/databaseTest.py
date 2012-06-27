import unittest

class findDirectoryTest(unittest.TestCase):
    """ Test that the extension can find the testing data """
    def setUp(self):
        import os
        import sys
        import slicer
        self.module = slicer.modules.slicerderivedimageeval

    def test_moduleLocation(self):
        extensionDir = '/scratch/welchdm/src/Slicer-extensions/SlicerDerivedImageEval/'
        assert self.module.widgetRepresentation().__file__ == extensionDir
