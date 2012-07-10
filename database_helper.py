import warnings

import module_locator

globals()['__file__'] = module_locator.module_path()

class sqliteDatabase(object):
    """ Connect to the SQLite database and prevent multiple user collisions
        during evaluations

    """

    def __init__(self, arraySize):
        import sqlite3
        globals()['sql'] = sqlite3
        self.database = None
        self.isolation_level = "EXCLUSIVE"
        self.connection = None
        self.cursor = None
        self.arraySize = arraySize
        self.createTestDatabase()

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
            self.cursor.close(); self.cursor = None
            self.connection.close(); self.connection = None
            fid.close()

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
            ids = ids + (row['record_id'],)
            idString += "?,"
        idString = idString[:-1]
        self.cursor.execute("UPDATE derived_images \
                             SET status='L' \
                             WHERE record_id IN ({0})".format(idString), ids)
        self.cursor.connection.commit()

    def lockAndReadRecords(self):
        self.openDatabase()
        try:
            rows = self.getBatch()
            self.lockBatch(rows)
        finally:
            self.connection.close()
        return rows

    def writeAndUnlockRecord(self, columns, values):
        self.database.openDatabase()
        columnString = ', '.join(columns)
        valueString = ()
        for value in values:
            valueString = valueString + ('%s',)
        valuesString = ', '.join(values)
        sqlCommand = "INSERT INTO image_reviews ({0}) VALUES \
                      ({1})".format(columnString, valueString)
        print sqlCommand
        try:
            self.cursor.execute(sqlCommand, values)
            self.cursor.execute("UPDATE derived_images \
                                 SET status='R' \
                                 WHERE record_id=? AND status='L'", (values(0),))
            self.cursor.commit()
        finally:
            self.connection.close()


class postgresDatabase(object):
    """ """
    def __init__(self, host, port, database, user, password=None, arraySize=1):
        import psycopg2 as sql
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.arraySize = arraySize

    def openDatabase(self):
        connnection = sql.connect(host=self.host, port=self.port,
                                  database=self.database, user=self.user,
                                  password=self.password)
        self.cursor = self.connection.cursor()
        self.cursor.arraysize = self.arraySize
