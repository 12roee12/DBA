import socket


class Local_server:

    def __init__(self):
        self.PORT = 1729
        self.IP = "127.0.0.1"
        self.MAX_MSG_LENGTH = 1024
        # setting up server stuff
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.IP, self.PORT))
        self.server_socket.listen()
        (self.client_socket, self.client_address) = self.server_socket.accept()

    def recieve_data(self):
        # the local server handles files only.
        file_length = int(self.client_socket.recv(8).decode()) # to get the length of the file
        data = b''
        while file_length > self.MAX_MSG_LENGTH:
            data = data + self.client_socket.recv(self.MAX_MSG_LENGTH)
            file_length = file_length - self.MAX_MSG_LENGTH
        if file_length != 0:
            data = data + self.client_socket.recv(file_length)
        return data

    def handle_files(self):
        data = self.recieve_data()
        self.send_data(data)

    def send_data(self, data):
        data_length = str(len(data)).zfill(8)
        msg = data_length + data.decode()
        self.client_socket.send(msg.encode())


if __name__ == "__main__":
    ls = Local_server()
