import select
import socket
import hashlib  # for one-side-encryption (for passwords)
import shutil

from flask import session  # stuff for the website to work
from Db_handler import Db_handler


class Server:

    def __init__(self):
        self.MAX_MSG_LENGTH = 1024
        self.SERVER_PORT = 5000
        self.SERVER_IP = "0.0.0.0"

        print("setting up server..")
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.SERVER_IP, self.SERVER_PORT))
        self.server_socket.listen()
        print("listening for clients...")
        # create a list of all the connected sockets.
        self.open_client_sockets = []
        self.open_client_names = []
        self.messages_to_send = []
        self.db = Db_handler()

    def new_client(self, current_socket):
        connection, client_address = current_socket.accept()
        print("New client joined!", client_address)
        self.open_client_sockets.append(connection)

    def end_connection(self, current_socket):
        # when client wants to close connection
        self.open_client_sockets.remove(current_socket)
        current_socket.close()
        print("client left")

    def read_data(self, current_socket):
        # handles one msg from client
        order = current_socket.recv(1).decode()
        # there are no orders 7 and 8 because there were such orders but i figured i dont need them.
        if order == "9":
            # means client wants to close connection
            self.end_connection(current_socket)
        elif order == "5":
            # means client wants to upload new chart to the website
            self.handle_order_5(current_socket)
        else:
            data = current_socket.recv(self.MAX_MSG_LENGTH).decode()
            if order == "1":
                # 1 = client wants to log in
                # how msg looks: name_length (zfilled 2) + name + password_length (zfilled 2) + password
                self.messages_to_send.append((current_socket, self.login(data)))
            elif order == "2":
                # 2 = client wants to sign up
                # name_length (zfilled 2) + name + password_length (zfilled 2) + password
                self.sign_up(data)
            elif order == "4":
                # means client wants to write a comment to some chart
                # data = chart_name_length (zfilled 2) + chart_name + name_length
                # + name + content
                self.comment(data)
            elif order == "3":
                # means client wants to get specific chart and comments
                file_data = self.get_chart(data)
                comments = self.get_comments(data)
                msg = bytes("3".encode()) + bytes(str(len(file_data)).encode()).zfill(8) + file_data + \
                      bytes(str(len(comments)).encode()).zfill(8) + bytes(comments.encode())
                self.messages_to_send.append((current_socket, msg))
            elif order == "6":
                # means client wants to get charts according to specific genre
                charts = self.get_by_genre(data)
                msg = "2" + str(len(charts)).zfill(8) + charts
                self.messages_to_send.append((current_socket, msg))

    def get_file(self, current_socket):
        # data = song_name_length (zfilled 2) + song_name + file_length (zfilled 8) + file
        # opens a new file with the data inside
        name_length = int(current_socket.recv(2).decode())
        name = current_socket.recv(name_length).decode()
        name = name + ".pdf"
        file_length = int(current_socket.recv(8).decode())
        data = b''
        while file_length > self.MAX_MSG_LENGTH:
            packet = current_socket.recv(self.MAX_MSG_LENGTH)
            data = data + packet
            file_length = file_length - self.MAX_MSG_LENGTH
        if file_length != 0:
            data = data + current_socket.recv(file_length)
        file_name = 'templates\\files\\' + name
        f = open(file_name, "wb")
        f.write(data)
        f.close()

    def read_list(self, rlist):
        for current_socket in rlist:
            if current_socket is self.server_socket:
                self.new_client(current_socket)
            else:
                self.read_data(current_socket)

    @staticmethod
    def convert_list_to_string(start_list):
        return str(start_list)

    def send_data(self, wlist):
        for message in self.messages_to_send:
            current_socket, data = message
            if current_socket in wlist:
                if type(data) == str:
                    current_socket.send(data.encode())
                else:
                    current_socket.send(data)
            self.messages_to_send.remove(message)

    def run(self):
        while True:
            rlist, wlist, xlist = select.select([self.server_socket] + self.open_client_sockets,
                                                self.open_client_sockets, [])
            self.read_list(rlist)
            self.send_data(wlist)

    def login(self, data):
        # handles the login.
        # data = name_length (zfilled 2) + name + password
        name_length = int(data[0:2])
        name = data[2: name_length + 2]
        password = data[name_length + 2:]
        password = hashlib.md5(password.encode()).hexdigest()
        task = "SELECT * FROM customers WHERE name = %(name)s AND password = %(password)s"
        info = {'name': name, 'password': password}
        msg = self.db.request_get_where(task, info)
        self.db.commit()
        if msg is not None:
            return "1True"
        else:
            return "1False"

    def sign_up(self, data):
        # handles signing up
        # data = name_length (zfilled 2) + name + password_length (zfilled 2) + password
        name_length = int(data[0: 2])
        name = data[2: name_length + 2]
        password = data[name_length + 2:]
        password = hashlib.md5(password.encode()).hexdigest()
        task = "INSERT INTO customers (name, password) VALUES (%(name)s, %(password)s)"
        info = {'name': name, 'password': password}
        self.db.request_insert(task, info)
        self.db.commit()

    @staticmethod
    def get_chart(data):
        # handles getting charts from client
        name = data
        file = "templates\\files\\" + name + ".pdf"
        f = open(file, 'rb')
        data = f.read()
        return data

    def get_comments(self, data):
        chart_name = data
        comments = self.db.request_get_all(f'SELECT * FROM {chart_name}')
        self.db.commit()
        comments = self.convert_list_to_string(comments)
        return comments

    def comment(self, data):
        # data = chart_name_length (zfilled 2) + chart_name + name_length + name + content
        chart_name_length = int(data[0:2])
        chart_name = data[2: chart_name_length + 2]
        name_length = int(data[chart_name_length + 2: chart_name_length + 4])
        name = data[chart_name_length + 4: chart_name_length + 4 + name_length]
        content = data[chart_name_length + 4 + name_length:]
        task = f'INSERT INTO {chart_name} (name, comment) VALUES (%(name)s, %(comment)s)'
        values = {'name': name, 'comment': content}
        self.db.request_insert(task, values)
        self.db.commit()

    def upload(self, current_socket):
        song_name_length = int(current_socket.recv(2).decode())
        name = current_socket.recv(song_name_length).decode()
        genre_length = int(current_socket.recv(1).decode())
        genre = current_socket.recv(genre_length).decode()
        name = name.replace("'", "")
        name = name.replace('"', '')
        task = 'INSERT INTO charts (name, genre, likes) VALUES (%(name)s, %(genre)s, %(likes)s)'
        info = {'name': name, 'genre': genre, 'likes': 0}
        self.db.request_insert(task, info)
        name = name.replace(" ", "_")
        name = name.lower()
        self.db.create_table(name)

    def get_by_genre(self, data):
        if data == "none":
            charts = self.db.request_get_all('SELECT * FROM charts')
            charts = self.convert_list_to_string(charts)
            return charts
        self.db.cursor.execute('SELECT * FROM charts WHERE genre = %(genre)s', {"genre": data})
        charts = self.db.cursor.fetchall()
        self.db.commit()
        charts = self.convert_list_to_string(charts)
        return charts

    def handle_order_5(self, current_socket):
        self.upload(current_socket)
        self.get_file(current_socket)


if __name__ == "__main__":
    s = Server()
    s.run()

