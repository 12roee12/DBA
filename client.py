import os
import pickle
import socket
import webbrowser

from flask import Flask, render_template, request, flash, url_for, session, send_file
from werkzeug.utils import redirect

app = Flask(__name__)
app.config['SECRET_KEY'] = 'de36039d4efd74a5e51ab16869e554fc'


class Client:

    def __init__(self):
        # in session client keeps info about user that might
        # be used while the user goes between pages.
        self.session = session
        self.MAX_MSG_LENGTH = 1024
        # connect to server
        self.server_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_connection.connect(("192.168.0.156", 5000))

    def send_to_server(self, msg):
        # sends msgs to the server
        # the type of the msg might be bytes or string
        if type(msg) == str:
            self.server_connection.send(msg.encode())
        else:
            self.server_connection.send(msg)

    def recv_info_from_server(self):
        order = self.server_connection.recv(1).decode()
        if order == "1":
            # means server sent answer about whether the user put correct registration details or not
            return self.is_valid()
        elif order == "2":
            # gets all the names of the charts
            data = convert_to_list(self.get_data().decode())
            return data
        elif order == "3":
            # gets specific file with his comments
            return self.get_data(), self.get_data()

    def is_valid(self):
        # the server sends or "True" or "False"
        return bool(self.server_connection.recv(self.MAX_MSG_LENGTH).decode())

    def get_data(self):
        # gets long data from server
        # length is zfilled to 8 in advance
        # returns data in bytes
        length = int(self.server_connection.recv(8).decode())
        data = b''
        while length > self.MAX_MSG_LENGTH:
            data = data + self.server_connection.recv(self.MAX_MSG_LENGTH)
            length = length - self.MAX_MSG_LENGTH
        if length != 0:
            data = data + self.server_connection.recv(length)
        return data


app.c = Client()


def convert_to_list(data):
    try:
        return eval(data)
    except:
        flash("Something didn't work. Maybe try again what you did :(")
        return redirect(url_for('home'))


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
        if "file" in app.c.session:
            os.remove(app.c.session["file"])
            app.c.session.pop("file", None)
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
        if "file" in app.c.session:
            os.remove(app.c.session["file"])
        if request.method == 'POST':
            form_data = request.form
            comment = form_data.getlist('content')
            msg = "4" + str(len(chart_name)).zfill(2) + chart_name + str(len(app.c.session["name"])).zfill(2) \
                  + app.c.session["name"] + str(comment)
            app.c.send_to_server(msg)
            comment = [app.c.session["name"], comment]
            app.c.session["comments"].append(comment)
            return render_template('chart.html', comments=app.c.session["comments"],
                                   len=len(app.c.session["comments"]), name=chart_name)
        else:
            msg = "3" + chart_name
            app.c.send_to_server(msg)
            data, comments = app.c.recv_info_from_server()
            comments = convert_to_list(comments)
            app.c.session["comments"] = comments
            create_file(chart_name, data)
            app.c.session["file"] = chart_name + ".pdf"
            return render_template('chart.html', comments=comments,
                                   len=len(comments), name=chart_name)
    return redirect('/')


@app.route('/upload', methods=['POST', 'GET'])
def upload():
    if "name" in app.c.session:
        if "file" in app.c.session:
            os.remove(app.c.session["file"])
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
            data = file.read()
            file.close()
            len_data = str(len(data)).zfill(8)
            msg = "5" + str(len(name)).zfill(2) + name + str(len(genre)) + genre + str(len_data).zfill(8)
            msg = bytes(msg.encode()) + data
            app.c.send_to_server(msg)
            return redirect('/home_page')
    return redirect('/')


@app.route('/download/<path:path>')
def download_file(path):
    path = path + ".pdf"
    return send_file(path, as_attachment=True)


@app.route('/leave')
def leave():
    if "file" in app.c.session:
        os.remove(app.c.session["file"])
        app.c.session.pop("file", None)
    app.c.session.pop("name", None)
    app.c.send_to_server("9")
    app.c.server_connection.close()
    return "BA-BAYY :)"


def create_file(name, data):
    name = name + '.pdf'
    file = open(name, 'ab')
    pickle.dump(data, file)
    file.close()


if __name__ == "__main__":
    # runs the website, with debug option
    app.run(debug=True, use_debugger=True, use_reloader=False, passthrough_errors=True)
    webbrowser.open("http://local_host:5000")
