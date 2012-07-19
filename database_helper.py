import warnings

import module_locator

globals()['__file__'] = module_locator.module_path()

class sqliteDatabase(object):
    """ Connect to the SQLite database and prevent multiple user collisions
        during evaluations

    """
    def __init__(self, login, arraySize):
        import sqlite3
        globals()['sql'] = sqlite3
        self.database = None
        self.isolation_level = "EXCLUSIVE"
        self.connection = None
        self.cursor = None
        self.reviewer_login = login
        self.reviewer_id = None
        self.arraySize = arraySize
        self.createTestDatabase()
        self.getReviewerID()

    def createTestDatabase(self):
        """ Create a dummy database file"""
        import os
        self.database = os.path.join(__file__, 'Testing', 'sqlTest.db')
        if os.path.exists(self.database):
            os.remove(self.database)
        self.openDatabase()
        # TODO: Upload test data to Midas for testing.
        testDatabaseCommands = os.path.join(__file__, 'Testing', 'databaseSQL.txt')
        fid = open(testDatabaseCommands, 'rb')
        try:
            commands = fid.read()
            self.connection.executescript(commands)
        finally:
            self.closeDatabase()
            fid.close()

    def getReviewerID(self):
        self.openDatabase()
        self.cursor.execute("SELECT reviewer_id FROM reviewers \
                             WHERE login=?", (self.reviewer_login,))
        self.reviewer_id = self.cursor.fetchone()
        self.closeDatabase()

    def openDatabase(self):
        self.connection = sql.connect(self.database, isolation_level=self.isolation_level)
        self.connection.row_factory = sql.Row
        self.cursor = self.connection.cursor()
        self.cursor.arraysize = self.arraySize

    def getBatch(self):
        self.cursor.execute("SELECT * \
                            FROM derived_images \
                            WHERE status = 'U'")
        rows = self.cursor.fetchmany()
        if not rows:
            raise warnings.warn("No rows were status == 'U' were found!")
        return rows

    def lockBatch(self, rows):
        # Lock batch members
        ids = ()
        idString = ""
        for row in rows:
            ids = ids + (str(row['record_id']),)
        idString = ', '.join(ids)
        sqlCommand = "UPDATE derived_images SET status='L' WHERE record_id IN ({0});".format(idString)
        self.connection.executescript(sqlCommand)
        self.connection.commit()

    def lockAndReadRecords(self):
        self.openDatabase()
        try:
            rows = self.getBatch()
            self.lockBatch(rows)
        finally:
            self.closeDatabase()
        return rows

    def writeAndUnlockRecord(self, values):
        self.openDatabase()
        reviewerID = self.reviewer_id[0]
        try:
            valueString = ("?, " * (len(values) + 1))[:-2]
            if len(values) == 17:
                sqlCommand = "INSERT INTO image_reviews \
                              ('record_id', 't2_average', 't1_average', \
                               'labels_tissue', 'caudate_left', 'caudate_right', \
                               'accumben_left', 'accumben_right', 'putamen_left', \
                               'putamen_right', 'globus_left', 'globus_right', \
                               'thalamus_left', 'thalamus_right', 'hippocampus_left', \
                               'hippocampus_right', 'notes', 'reviewer_id'\
                               ) VALUES (%s)" % valueString
            elif len(values) == 16:
                # No notes
                print "No notes???"
            print sqlCommand
            self.cursor.execute(sqlCommand, values + (reviewerID,))
            self.cursor.execute("UPDATE derived_images \
                                 SET status='R' \
                                 WHERE record_id=? AND status='L'", (values[0],))
            self.connection.commit()
        except:
            print columns + ('reviewer_id',)
            print "Column length: %d" % len(columns + ('reviewer_id',))
            print values + (reviewerID,)
            print "Value length: %d" % len(values + (reviewerID,))
            raise
        finally:
            self.closeDatabase()

    def closeDatabase(self):
        self.cursor.close()
        self.cursor = None
        self.connection.close()
        self.connection = None


class postgresDatabase(object):
    """ Connect to the Postgres database and prevent multiple user collisions
        during simultaneous evaluations

    """
    def __init__(self, host, port, database, user, password=None, login=None, arraySize=1):
        import psycopg2
        globals()['sql'] = psycopg2
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.reviewer_login = login
        self.arraySize = arraySize
        self.connection = None
        self.cursor = None
        self.getReviewerID()
        self.isolationLevel = sql.extensions.ISOLATION_LEVEL_SERIALIZABLE

    def openDatabase(self):
        """ Open the database and create cursor and connection
        """
        self.connnection = sql.connect(host=self.host,
                                       port=self.port,
                                       database=self.database,
                                       user=self.user,
                                       password=self.password)
        self.cursor = self.connection.cursor()
        self.cursor.arraysize = self.arraySize
        self.cursor.cursor_factory = sql.extras.DictCursor

    def closeDatabase(self):
        """ Close cursor and connection, setting values to None
        """
        self.cursor.close()
        self.cursor = None
        self.connection.close()
        self.connection = None

    def getReviewerID(self):
        """ Using the database login name, get the reviewer_id key from the reviewers table
        """
        self.openDatabase()
        self.cursor.execute("SELECT reviewer_id FROM reviewers \
                             WHERE login=?", (self.reviewer_login,))
        self.reviewer_id = self.cursor.fetchone()
        self.closeDatabase()

    def getBatch(self):
        """ Return a dictionary of rows where the number of rows == self.arraySize and status == 'U'
        """
        self.cursor.execute("SELECT * \
                            FROM derived_images \
                            WHERE status = 'U'")
        rows = self.cursor.fetchmany()
        if not rows:
            raise warnings.warn("No rows were status == 'U' were found!")
        return rows

    def lockBatch(self, rows):
        """ Set the status of all batch members to 'L'
            Arguments:
            - `rows`: The dictionary-like list of rows resulting from a call to the cursor.fetchmany()
        """
        ids = ()
        idString = ""
        for row in rows:
            ids = ids + (str(row['record_id']),)
        idString = ', '.join(ids)
        sqlCommand = "UPDATE derived_images \
                      SET status='L' \
                      WHERE record_id IN ({0})".format(idString)
        self.cursor.execute(sqlCommand)
        self.connection.commit()

    def lockAndReadRecords(self):
        """ Find a given number of records with status == 'U', set the status to 'L', and return the records in a dictionary-like object
        """
        self.openDatabase()
        try:
            rows = self.getBatch()
            self.lockBatch(rows)
        finally:
            self.closeDatabase()
        return rows

    def writeAndUnlockRecord(self, columns, values):
        """ Open the database, insert the evaluation values into the image_reviews table, and update the status == 'R' for the record_id
            Arguments:
            - `columns`: a tuple of columns from the image_reviews table, minus 'reviewer_id'
            - `values`: a tuple of the corresponding values for the columns tuple
        """
        self.openDatabase()
        columnString = ', '.join(('reviewer_id',) + columns)
        valueString = ', '.join((str(self.reviewer_id[0]),) + values)
        # for value in values:
        #     valueString = valueString + ('?',)
        # valuesString = ', '.join(valueString)
        sqlCommand = "INSERT INTO image_reviews ({0}) VALUES ({1})".format(columnString, valueString)
        print sqlCommand
        try:
            self.cursor.execute(sqlCommand)
            self.cursor.execute("UPDATE derived_images \
                                 SET status='R' \
                                 WHERE record_id=? AND status='L'", (values[1],))
            self.connection.commit()
        finally:
            self.closeDatabase()
