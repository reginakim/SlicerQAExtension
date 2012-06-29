import sqlite3 as sql

import module_locator

globals()['__file__'] = module_locator.module_path()

class databaseInterface(object):
    """ Connect to the SQLite database and prevent multiple user collisions
        during evaluations

    """

    def __init__(self, *args):
        self.database = None
        self.isolation_level = "IMMEDIATE"
        self.connection = None
        # self.row_factory = None
        # self.connection.isolation_level = self.isolation_level
        self.cursor = None
        self.arraySize = None

    def createTestDatabase(self):
        """ Create a dummy database file"""
        import os
        self.database = os.path.join(__file__, 'Testing', 'test.db')
        # TODO: Generalize text file for testing elsewhere.
        # TODO: Upload test data to Midas for testing.
        testDatabaseCommands = os.path.join(__file__, 'Testing', 'databaseSQL.txt')
        self.connection = sql.connect(self.database)
        self.connection.row_factory = sql.Row
        self.cursor = self.connection.cursor()
        fid = open(testDatabaseCommands)
        try:
            lines = readlines(fid)
            for line in readlines:
                self.cursor.execute(line)
        finally:
            fid.close()
            self.connection.close()

    def openDatabase(self, batchSize=1):
        self.connection = sql.connect(self.database, self.isolation_level)
        self.cursor = self.connection.cursor()
        self.cursor.arraysize = batchSize

    def getBatchIDs(self):
        # Get batch
        self.cursor.execute("SELECT record_id \
                            FROM derived_images \
                            WHERE status = 'unreviewed'")
        ids = self.cursor.fetchmany()
        if not ids:
            # TODO: This shouldn't be an exception - should halt gracefully
            self.connection.close()
            raise Exception("No rows were status == 'unreviewed' were found!")
        return ids

    def lockBatchRows(self, ids):
        # Lock batch members
        for ID in ids:
            self.cursor.execute("UPDATE derived_images \
                                 SET status=? \
                                 WHERE id=?", ('locked', ID[0]))
        self.cursor.connection.commit()

    def readBatchInformation(self, ids):
        batch = []
        for ID in ids:
            self.cursor.execute("SELECT id, analysis, project, subject, session \
                                 FROM derived_images \
                                 WHERE record_id=? AND status='locked'", ID)
            batch.append(self.cursor.fetchone())
        return batch

    def lockAndReadRecords(self):
        print self.openDatabase()
        try:
            ids = self.getBatchIDs()
            self.lockBatchRows(ids)
            self.batchRows = self.readBatchInformation(ids)
        except Exception, e:
            raise e
        finally:
            self.connection.close()
