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
        self.rows = None
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
        self.rows = self.cursor.fetchmany()
        if not self.rows:
            raise warnings.warn("No rows were status == 'U' were found!")

    def lockBatch(self):
        # Lock batch members
        ids = ()
        idString = ""
        for row in self.rows:
            ids = ids + (str(row['record_id']),)
        idString = ', '.join(ids)
        sqlCommand = "UPDATE derived_images SET status='L' WHERE record_id IN ({0});".format(idString)
        self.connection.executescript(sqlCommand)
        self.connection.commit()

    def lockAndReadRecords(self):
        self.openDatabase()
        try:
            self.getBatch()
            self.lockBatch()
        finally:
            self.closeDatabase()
        return self.rows

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
        try:
            import pg8000
        except ImportError:
            ### Hack to import pg8000 locally
            import os
            import sys
            pg8kDir = [os.path.join(__file__, 'Resources', 'Python', 'pg8000-1.08')]
            newSysPath = pg8kDir + sys.path
            sys.path = newSysPath
            import pg8000
        globals()['sql'] = pg8000.DBAPI
        sql.paramstyle = "qmark"
        self.rows = None
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.reviewer_login = login
        self.arraySize = arraySize
        self.connection = None
        self.cursor = None
        self.reviewer_id = None
        # self.isolationLevel = sql.extensions.ISOLATION_LEVEL_SERIALIZABLE

    def openDatabase(self):
        """ Open the database and create cursor and connection
        """
        self.connection = sql.connect(host=self.host,
                                      port=self.port,
                                      database=self.database,
                                      user=self.user,
                                      password=self.password)
        self.cursor = self.connection.cursor()
        self.cursor.arraysize = self.arraySize

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
        try:
            self.reviewer_id = self.cursor.fetchone()[0]
        except TypeError:
            raise pg8000.errors.DataError("The reviewer is not found in the database!  Contact the developers for assistance.")
        finally:
            print "The reviewer is: %s" % self.reviewer_login
            self.closeDatabase()

    def getBatch(self):
        """ Return a dictionary of rows where the number of rows == self.arraySize and status == 'U'
        """
        self.cursor.execute("SELECT * \
                            FROM derived_images \
                            WHERE status = 'U'")
        self.rows = self.cursor.fetchmany()
        if not self.rows:
            raise warnings.warn("No rows were status == 'U' were found!")

    def lockBatch(self):
        """ Set the status of all batch members to 'L'
        """
        ids = ()
        idString = ""
        for row in self.rows:
            record_id = row[0]
            ids = ids + (record_id,)
        idString = ("?, " * self.arraySize)[:-2]
        sqlCommand = "UPDATE derived_images \
                      SET status='L' \
                      WHERE record_id IN ({0})".format(idString)
        self.cursor.execute(sqlCommand, ids)
        self.connection.commit()

    def lockAndReadRecords(self):
        """ Find a given number of records with status == 'U', set the status to 'L',
            and return the records in a dictionary-like object
        """
        self.openDatabase()
        try:
            self.getBatch()
            self.lockBatch()
        finally:
            self.closeDatabase()
        return self.rows

    def writeReview(self, values):
        """ Write the review values to the postgres database

        Arguments:
        - `values`:
        """
        self.getReviewerID()
        self.openDatabase()
        try:
            valueString = ("?, " * (len(values) + 1))[:-2]
            sqlCommand = "INSERT INTO image_reviews \
                            (record_id, t2_average, t1_average, \
                            labels_tissue, caudate_left, caudate_right, \
                            accumben_left, accumben_right, putamen_left, \
                            putamen_right, globus_left, globus_right, \
                            thalamus_left, thalamus_right, hippocampus_left, \
                            hippocampus_right, notes, reviewer_id\
                            ) VALUES (%s)" % valueString
            self.cursor.execute(sqlCommand, values + (self.reviewer_id,))
            self.connection.commit()
        except:
            raise
        finally:
            self.closeDatabase()

    def unlockRecord(self, status='U', pKey=None):
        """ Unlock the record in derived_images by setting the status, dependent of the index value

        Arguments:
        - `pKey`: The value for the record_id column in the self.rows variable.
                  If pKey > -1, set that record's flag to 'R'.
                  If pKey is None, then set the remaining, unreviewed rows to 'U'
        """
        self.openDatabase()
        try:
            if not pKey is None:
                self.cursor.execute("UPDATE derived_images SET status=? \
                                     WHERE record_id=? AND status='L'", (status, pKey))
                self.connection.commit()
            else:
                for row in self.rows:
                    self.cursor.execute("SELECT status FROM derived_images WHERE record_id=?", (int(row[0]),))
                    currentStatus = self.cursor.fetchone()
                    if currentStatus[0] == 'L':
                        self.cursor.execute("UPDATE derived_images SET status='U' \
                                             WHERE record_id=? AND status='L'", (int(row[0]),))
                        self.connection.commit()
        except:
            raise
        finally:
            self.closeDatabase()
