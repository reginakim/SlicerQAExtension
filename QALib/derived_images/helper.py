#!/usr/bin/env python
import logging
import logging.handlers
import os
import warnings

from . import pg8000, sql

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

    def __init__(self, *args, **kwds):
        """ Set the class attributes needed for connecting to the database and interacting with it
        ------------------------
        Arguments:
        - `host`: The name of the host machine (default = 'localhost')
        - `port`: The port number (default = 5432)
        - `pguser`: The username to connect to the Postgres server with, default is 'postgres'
        - `database`: The name of the database to connect to.  If omitted, it is the same as the `user`
        - `password`: The password associated with the `user` on the Postgres server, default is 'postgres'
        - `login`: The reviewer login ID, normally $USER
        - `arraySize`: The number of rows to return
        - `dataTable`: the data table
        - `reviewTable`: the review table
        ------------------------
        >>> import os
        >>> db = postgresDatabase()
        >>> db != None
        True
        >>> db.host == 'localhost' and db.port == 5432 and db.pguser == 'postgres' and db.pguser == db.database and db.pguser == db.password and db.login == os.environ['USER'] and db.arraySize == 1
        True
        >>> # Test positional args
        >>> db = postgresDatabase('my.test.host', 0, 'myuser', None, 'pass', 'login', 15)
        >>> db != None
        True
        >>> db.host == 'my.test.host' and db.port == 0 and db.pguser == 'myuser' and db.pguser == db.database and db.password == 'pass' and db.login == 'login' and db.arraySize == 15
        True
        >>> # Test a mix
        >>> db = postgresDatabase('my.test.host', 'myuser', port=15, database='postgres', arraySize=15, password='pass', pguser='login')
        >>> db != None
        True
        >>> db.host == 'my.test.host' and db.port == 15 and db.pguser == 'login' and db.database == 'postgres' and db.password == 'pass' and db.login == 'myuser' and db.arraySize == 15
        True
        >>> # Test keyword args
        >>> db = postgresDatabase(host='my.test.host', arraySize=15, login='myuser', password='pass', database=None, pguser='login', port=15)
        >>> db != None
        True
        >>> db.host == 'my.test.host' and db.port == 15 and db.pguser == 'login' and db.pguser == db.database and db.password == 'pass' and db.login == 'myuser' and db.arraySize == 15
        True
        """
        sql.paramstyle = "qmark"
        self.rows = None
        self.connection = None
        self.cursor = None
        # self.isolationLevel = sql.extensions.ISOLATION_LEVEL_SERIALIZABLE
        # Set defaults
        self.host = 'localhost'
        self.port = 5432
        self.pguser = 'postgres'
        self.database = None
        self.password = 'postgres'
        self.login = os.environ['USER']
        self.arraySize = 1
        # Set inputs
        keys = ['host', 'port', 'pguser', 'database', 'password', 'login', 'arraySize', 'logging', 'dataTable', 'reviewTable']
        keys.reverse()
        args = list(args)
        for key in keys:
            value = kwds.pop(key, None)
            if value is None:
                value = args.pop()
            self.__setattr__(key, value)
        # Set the database default
        if self.database is None: self.database = self.pguser

    def openDatabase(self):
        """ Open the database and create cursor and connection
        >>> db = postgresDatabase()
        >>> db.openDatabase()
        >>> import pg8000 as sql
        >>> isinstance(db.connection, sql.DBAPI.ConnectionWrapper)
        True
        >>> isinstance(db.cursor, sql.DBAPI.CursorWrapper)
        True
        """
        self.logging.debug("call")
        self.connection = sql.connect(host=self.host,
                                      port=self.port,
                                      database=self.database,
                                      user=self.pguser,
                                      password=self.password)
        self.cursor = self.connection.cursor()
        self.cursor.arraysize = self.arraySize

    def closeDatabase(self):
        """ Close cursor and connection, setting values to None
        """
        self.logging.debug("call")
        self.cursor.close()
        self.cursor = None
        self.connection.close()
        self.connection = None

    def getReviewerID(self):
        """ Using the database login name, get the reviewer_id key from the reviewers table
        ------------------------
        >>> db = postgresDatabase(host='opteron.psychiatry.uiowa.edu', pguser='tester', database='test', password='test1', login='user1')
        >>> db.getReviewerID(); db.reviewer_id == 1;
        True
        >>> db = postgresDatabase(host='opteron.psychiatry.uiowa.edu', pguser='tester', database='test', password='test1', login='user0')
        >>> db.getReviewerID();
        Traceback (most recent call last):
            ...
        DataError: Reviewer user0 is not registered in the database test!
        """
        self.logging.debug("call")
        self.openDatabase()
        self.cursor.execute("SELECT reviewer_id FROM reviewers \
                             WHERE login=?", (self.login,))
        try:
            self.reviewer_id = self.cursor.fetchone()[0]
        except TypeError:
            raise pg8000.errors.DataError("Reviewer %s is not registered in the database %s!" % (self.login, self.database))
        finally:
            self.closeDatabase()

    def getBatch(self):
        """ Return a dictionary of rows where the number of rows == self.arraySize and status == 'U'
        ----------------------
        >>> db = postgresDatabase(host='opteron.psychiatry.uiowa.edu', pguser='tester', database='test', password='test1', login='user1')
        >>> db.getBatch()
        Traceback (most recent call last):
            ...
        AttributeError: 'NoneType' object has no attribute 'execute'
        >>> db.openDatabase(); db.getBatch(); db.closeDatabase()
        >>> self.rows is None
        True
        """
        self.logging.debug("call")
        self.logging.debug( self.dataTable )

        mycmd = "SELECT * FROM " + self.dataTable + " WHERE status = 'U' ORDER BY priority" 
        self.logging.debug( mycmd )
        self.cursor.execute( mycmd )
        ### HACKED
        #self.cursor.execute("SELECT * FROM ? WHERE status = 'U' ORDER BY priority", 
        #                    (self.dataTable,))
        ### END HACKED
        self.rows = self.cursor.fetchmany()
        if not self.rows:
            raise pg8000.errors.DataError("No rows were status == 'U' were found!")

    def lockBatch(self):
        """ Set the status of all batch members to 'L'
        """
        self.logging.debug("call")
        ids = ()
        idString = ""
        for row in self.rows:
            record_id = row[0]
            ids = ids + (record_id,)
        idString = ("?, " * self.arraySize)[:-2]
        sqlCommand = "UPDATE {dataTable} \
                      SET status='L' \
                      WHERE record_id IN ({idString})".format(dataTable=self.dataTable, idString=idString)
        self.cursor.execute(sqlCommand, ids)
        self.connection.commit()

    def lockAndReadRecords(self):
        """ Find a given number of records with status == 'U', set the status to 'L',
            and return the records in a dictionary-like object
        """
        self.logging.debug("call")
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
        self.logging.debug("call")
        self.getReviewerID()
        self.openDatabase()
        try:
            valueString = ("?, " * (len(values) + 1))[:-2]
            print "valueString = " + valueString
            print ( "reviewTable:::::" + self.reviewTable )
            sqlCommand = "INSERT INTO {reviewTable}".format(reviewTable=self.reviewTable) + \
                         "  (record_id, t1_average, \
                            caudate_left, caudate_right, \
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
        self.logging.debug("call")
        self.openDatabase()
        try:
            if not pKey is None:
                print( "::self.dataTable = " +self.dataTable +
                     "::status = " + status +
                     "::pKey = {0}".format(pKey) )
                PLEASE_Work_Cmd = "UPDATE {0} SET status='{1}' WHERE record_id={2} AND status='L'".format(self.dataTable, status, pKey)
                print "PLEASE_Work_Cmd == " + PLEASE_Work_Cmd
                self.cursor.execute( PLEASE_Work_Cmd )
                #self.cursor.execute("UPDATE ? SET status=? WHERE record_id=? AND status='L'", (self.dataTable, status, pKey))
                self.connection.commit()
            else:
                for row in self.rows:
                    self.cursor.execute("SELECT status FROM ? WHERE record_id=?", (self.dataTable, int(row[0])))
                    currentStatus = self.cursor.fetchone()
                    if currentStatus[0] == 'L':
                        self.cursor.execute("UPDATE ? SET status='M' \
                                             WHERE record_id=? AND status='L'", (self.dataTable, int(row[0])))
                        self.connection.commit()
        except:
            raise
        finally:
            self.closeDatabase()

if __name__ == "__main__":
    import doctest
    import pg8000
    doctest.testmod()
