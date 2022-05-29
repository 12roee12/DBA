import hashlib
import socket
import webbrowser

from flask import Flask, render_template, request, flash, url_for, session
from werkzeug.utils import redirect

app = Flask(__name__)
app.config['SECRET_KEY'] = 'de36039d4efd74a5e51ab16869e554fc'


class Client:

    def __init__(self):
        self.session = session
        self.MAX_MSG_LENGTH = 1024
        # connect to local server
        # self.local_server_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.local_server_connection.connect(("127.0.0.1", 1729))
        # connect to server
        self.server_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_connection.connect(("127.0.0.1", 5000))

    def send_to_server(self, msg):
        self.server_connection.send(msg.encode())

    def send_file_to_local_server(self, data):
        msg = str(len(data)).zfill(8) + str(data)
        self.local_server_connection.send(msg.encode())

    def recv_from_local_server(self):
        pass

    def recv_info_from_server(self):
        order = self.server_connection.recv(1).decode()
        if order == "1":
            return self.is_valid()
        elif order == "2":
            return eval(self.get_charts())
        elif order == "3":
            self.send_file_to_local_server(self.get_file_from_server())
        elif order == "4":
            self.get_comments()

    def is_valid(self):
        return bool(self.server_connection.recv(self.MAX_MSG_LENGTH).decode())

    def get_charts(self):
        data_length = int(self.server_connection.recv(8).decode())
        charts = ""
        while data_length > self.MAX_MSG_LENGTH:
            charts = charts + self.server_connection.recv(self.MAX_MSG_LENGTH).decode()
            data_length = data_length - self.MAX_MSG_LENGTH
        if data_length != 0:
            charts = charts + self.server_connection.recv(data_length).decode()
        return charts

    def get_file_from_server(self):
        length = int(self.server_connection.recv(8).decode())
        data = b''
        while length > self.MAX_MSG_LENGTH:
            data = data + self.server_connection.recv(self.MAX_MSG_LENGTH)
            length = length - self.MAX_MSG_LENGTH
        if length != 0:
            data = data + self.server_connection.recv(length)
        return data

    def get_comments(self):
        length = int(self.server_connection.recv(8).decode())
        data = ""
        while length > self.MAX_MSG_LENGTH:
            data = data + self.server_connection.recv(self.MAX_MSG_LENGTH).decode()
            length = length - self.MAX_MSG_LENGTH
        if length != 0:
            data = data + self.server_connection.recv(length).decode()
        return data


app.c = Client()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        # getting the username and password, and making necessary changes.
        form_data = request.form
        name = str(form_data.getlist("username"))
        name = name[2:-2]
        if name is not None:
            password = str(form_data.getlist("password"))[2:-2]
            msg = "1" + str(len(name)).zfill(2) + name + password
            app.c.send_to_server(msg)
            validation = app.c.recv_info_from_server()
            if validation:
                app.c.session["name"] = name
                return redirect(url_for('home'))
        else:
            flash("name or password are not good")
    else:
        return redirect(url_for('index'))


@app.route('/signup', methods=['POST', 'GET'])
def sign_up():
    if request.method == 'GET':
        return render_template('signup.html')
    else:
        form_data = request.form
        name = str(form_data.getlist("username"))
        name = name[2:-2]
        if name is not None:
            password = form_data.getlist("password")[0]
            re_right = form_data.getlist("re_right")[0]
            if password == re_right and password is not None:
                msg = "2" + str(len(name)).zfill(2) + name + password
                app.c.send_to_server(msg)
                app.c.session["name"] = name
                return redirect(url_for('home'))


@app.route('/home_page', methods=['POST', 'GET'])
def home():
    if "name" in app.c.session:
        if request.method == 'GET':
            msg = "6none"
            app.c.send_to_server(msg)
            charts = app.c.recv_info_from_server()
            return render_template('welcome.html', charts=charts, len=len(charts))
        form_data = request.form
        genre = form_data.getlist("genre")
        msg = "6" + str(genre)[2: -2]
        app.c.send_to_server(msg)
        charts = app.c.recv_info_from_server()
        return render_template('welcome.html', charts=charts, len=len(charts))
    return redirect('/')


@app.route('/home_page/<string:chart_name>', methods=['POST', 'GET'])
def chart(chart_name):
    if "name" in app.c.session:
        if request.method == 'POST':
            form_data = request.form
            comment = form_data.getlist('content')
            msg = "4" + str(len(chart_name)) + chart_name + str(len(app.c.session["name"])) \
                  + app.c.session["name"] + comment
        else:
            msg = "3" + chart_name
        app.c.send_to_server(msg)
        comments = app.c.recv_info_from_server()
        return render_template('chart.html', comments=comments,
                               len=len(comments), name=chart_name)
    return redirect('/')


@app.route('/upload', methods=['POST', 'GET'])
def upload():
    if "name" in app.c.session:
        if request.method == 'GET':
            return render_template('upload.html')
        # gets all the info from user
        name = request.form['name']
        genre = request.form['genre']
        file = request.files['file']
        # check that everything is here
        if not name:
            flash('Name is required!')
        elif not genre:
            flash('Genre is required!')
        elif not file:
            flash('Chart is required!')
        else:
            name = name.replace("'", "")
            name = name.replace(" ", "_")
            name = name.replace('"', '')
            name = name.lower()
            msg = "5" + str(len(name)) + name + genre
            app.c.send_to_server(msg)
            return redirect('/home_page')
    return redirect('/')


@app.route('/leave')
def leave():
    app.c.session["name"] = ""
    app.c.send_to_server("9")
    app.c.server_connection.close()


if __name__ == "__main__":
    # runs the website, with debug option
    app.run(debug=True, use_debugger=True, use_reloader=False, passthrough_errors=True)
    webbrowser.open("http://local_host:5000")
