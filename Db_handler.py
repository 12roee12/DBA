import mysql.connector


class Db_handler:
    def __init__(self):
        # opens the database to use
        self.db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="1234",
            database="first_db"
        )
        self.cursor = self.db.cursor()

    def request_get_all(self, request):
        # with this function I can get a complete table.
        self.cursor.execute(request)
        return self.cursor.fetchall()

    def request_get_where(self, request, where):
        # with this function I can get spcific data from table
        self.cursor.execute(request, where)
        return self.cursor.fetchall()

    def request_insert(self, request, stuff_to_insert):
        # with this function I can insert data into the database, such as username, password, and chart info.
        self.cursor.execute(request, stuff_to_insert)

    def commit(self):
        # to close the database.
        self.db.commit()
