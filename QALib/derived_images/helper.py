#!/usr/bin/env python
import os
import warnings
try:
    import psycopg2 as sql
    # from . import pg8000.DBAPI as sql
    # from . import pg8000.DBAPI.ConnectionWrapper as sql.connection
    # from . import pg8000.DBAPI.CursorWrapper as sql.cursor
except ValueError:
    if __name__ != "__main__":
        raise

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
        - `pguser`: The username to connect to the Postgres server with (default = 'postgres')
        - `database`: The name of the database to connect to.  If omitted, it is the same as the `user`
        - `password`: The password associated with the `user` on the Postgres server (default = 'postgres')
        - `login`: The reviewer login ID (default = $USER)
        - `arraySize`: The number of rows to return (default = 1)
        - `imageTable`: The database table to query for records (default = None)
        ------------------------

        """
        # Set internals
        validArgs = ('host', 'port', 'pguser', 'database', 'password', 'login', 'arraySize', 'imageTable')
        defaults = ('localhost', 5432, 'postgres', None, 'postgres', os.environ['USER'], 1, None)
        # sql.paramstyle = "qmark"
        self.rows = None
        self.connection = None
        self.cursor = None
        self.reviewer_id = None
        # self.isolationLevel = sql.extensions.ISOLATION_LEVEL_SERIALIZABLE
        # Set defaults
        argsList = list(args)
        for key in validArgs:
            if key in kwds.keys():
                value = kwds[key]
            elif len(argsList) != 0:
                value =  argsList.pop(0)
            else:
                value = defaults[validArgs.index(key)]
            setattr(self, key, value)
        # Set the database default to pguser
        if self.database is None:
            self.database = self.pguser

    def openDatabase(self):
        """ Open the database and create a cursor """
        self.connection = sql.connect(host=self.host, port=self.port, database=self.database,
                                      user=self.pguser, password=self.password)
        self.cursor = self.connection.cursor()
        self.cursor.arraysize = self.arraySize

    def closeDatabase(self):
        """ Close cursor and connection, setting values to None """
        self.cursor.close()
        self.cursor = None
        self.connection.close()
        self.connection = None

    def getReviewerID(self):
        """ Using the user login name, get the reviewer_id key from the reviewers table

        """
        self.openDatabase()
        try:
            self.cursor.execute("SELECT reviewer_id FROM reviewers WHERE login = %s", (self.login,))
            self.reviewer_id = self.cursor.fetchone()[0]
        except TypeError:
            raise ValueError("Reviewer %s is not registered in the database %s!" % (self.login, self.database))
        except:
            raise
        finally:
            self.closeDatabase()

    def getRecords(self, status='U', imageTable=None, **kwds):
        """ Return a dictionary of rows where the number of rows == self.arraySize

        """
        if imageTable is None:
            imageTable = self.imageTable
        assert not imageTable is None, 'The database table is not specified: value is "%s"' % imageTable
        assert self.cursor is not None, 'The database is not open! Run postgresDatabase.openDatabase()'
        try:
            self.cursor.execute("SELECT * FROM {0} WHERE status = %s ORDER BY priority".format(imageTable), (status,))
        except sql.ProgrammingError:
            raise ValueError("The table '%s' does not exist in the database!" % imageTable)
        except sql.InternalError:
            raise ValueError("The status '%s' is not a valid one" % status)
        except:
            raise
        self.rows = self.cursor.fetchmany()
        if self.rows is None:
            raise sql.DataError("No rows in table %s with status %s were found!" % (imageTable, status))

    # def lockRecords(self, imageTable=None):
    #     """ Set the status of all batch members to 'L'
    #     """
    #     if imageTable is None: imageTable = self.imageTable
    #     assert not imageTable is None, 'The database table is not specified: value is "%s"' % imageTable
    #     values = (imageTable,)
    #     for row in self.rows:
    #         record_id = row[0]
    #         self.lockRecord(record_id=record_id)

    def lockRecord(self, record_id=None, **kwds):
        """ Set the status of one record to 'L' for 'locked'
        """
        if record_id is None:
            record_id = self.rows[0][0]
        assert not self.imageTable is None, 'The database table is not specified: value is "%s"' % self.imageTable
        self.cursor.execute("UPDATE {0} SET status='L' WHERE record_id = %s",format(self.imageTable), (record_id,))
        self.connection.commit()

    def lockAndReadRecords(self, **kwds):
        """ Find a given number of records with status == 'U', set the status to 'L',
            and return the records in a dictionary-like object
        """
        self.openDatabase()
        print kwds
        try:
            self.getRecords(**kwds)
            self.lockRecord(**kwds)
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

if __name__ == "__main__":
    import doctest
    import os.path

    fileName = os.path.join('../', 'Testing', 'Python', 'test_helper.txt')
    doctest.testfile(fileName, module_relative=True, name='Database helper', package='QALib')
    # doctest.testmod()
