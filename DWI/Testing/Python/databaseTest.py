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

class writeReviewTest(unittest.TestCase):
    """ Test database writing capability """
    def setUp(self):
        import os
        import sys
        import slicer
        self.module = slicer.modules.slicerderivedimageeval
        self.logic = self.module.logic
        self.widget = {"regions":self.module.regions, "images":self.module.images}
        self.USER = os.environ["USER"]
        os.environ["USER"] = 'test'
        self.logic(self.widget, testing=False)

    def test_SetTestUSER(self):
        assert os.environ["USER"] =='test'
        assert self.logic.user_id == 'test'

    def test_WriteReview(self):
        database = self.logic.database
        recordID = {'unlocked':746, 'locked':747, 'reviewed':748}
        values = (recordID['locked'], ) + self.qaValueMap["good"]*15 + ("NULL,")
        # Verify that there are no test reviews
        database.openDatabase()
        database.cursor.execute("SELECT * from image_reviews WHERE reviewer_id = (select reviewer_id from reviewers where login = 'test')")
        assert database.cursor.fetchall() == ()
        database.closeDatabase()
        # Test database write function
        database.writeReview(values)
        database.openDatabase()
        database.cursor.execute("select reviewer_id from reviewers where login = 'test'")
        reviewer_id = database.cursor.fetchone()
        database.cursor.execute("SELECT * from image_reviews WHERE reviewer_id = '?", reviewer_id)
        review = database.cursor.fetchone()
        # Get around timestamp
        assert review[1:14] + review[-4:] == reviewer_id + values
        database.closeDatabase()

    def tearDown(self):
        os.environ["USER"] = self.USER

