import pickle
import socket

from flask import Flask, render_template, request, flash, url_for, session, send_file
from werkzeug.utils import redirect

app = Flask(__name__)
app.config['SECRET_KEY'] = 'de36039d4efd74a5e51ab16869e554fc'


class Frontend_server:

    def __init__(self):
        # in session client keeps info about user that might
        # be used while the user goes between pages.
        self.session = session
        self.MAX_MSG_LENGTH = 1024
        # find ip
        hostname = socket.gethostname()
        self.ip = socket.gethostbyname(hostname)
        # connect to server
        self.server_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_connection.connect((self.ip, 6000))

    def send_to_backend_server(self, msg):
        # sends msgs to the server
        # the type of the msg might be bytes or string
        if type(msg) == str:
            self.server_connection.send(msg.encode())
        else:
            self.server_connection.send(msg)

    def recv_info_from_backend_server(self):
        order = self.server_connection.recv(1).decode()
        if order == "1":
            # means server sent answer about whether the user put correct registration details or not
            return self.is_valid()
        elif order == "2":
            # gets all the names of the charts
            charts, genres = convert_to_list(self.get_data().decode()), convert_to_list(self.get_data().decode())
            return charts, genres
        elif order == "3":
            # gets specific file with his comments
            return self.get_data(), self.get_data()
        elif order == "4" or order == "5":
            return convert_to_list(self.get_data().decode())

    def is_valid(self):
        # the server sends or "True" or "False"
        val = self.server_connection.recv(self.MAX_MSG_LENGTH).decode()
        print(val)
        if val == "False":
            return False
        else:
            return True

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


app.fs = Frontend_server()


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
            app.fs.send_to_backend_server(msg)
            validation = app.fs.recv_info_from_backend_server()
            if validation:
                app.fs.session["name"] = name
                return redirect(url_for('home'))
            else:
                flash("name or password are not good")
                return redirect(url_for('index'))
        else:
            flash("name or password are not good")
            return redirect(url_for('index'))
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
                app.fs.send_to_backend_server(msg)
                app.fs.session["name"] = name
                return redirect(url_for('home'))
            else:
                flash("passwords are not the same")
                return redirect('/signup')
        else:
            flash("name is missing")
            return redirect('/signup')


@app.route('/home_page', methods=['POST', 'GET'])
def home():
    if "name" in app.fs.session:
        if request.method == 'GET':
            msg = "6none"
            app.fs.send_to_backend_server(msg)
            charts, genres = app.fs.recv_info_from_backend_server()
            new_genres = []
            for genre in genres:
                new_genres.append(genre[0])
            return render_template('welcome.html', charts=charts, len=len(charts), genres=new_genres, length=len(new_genres))
        form_data = request.form
        genre = form_data.getlist("genre")
        msg = "6" + genre[0]
        app.fs.send_to_backend_server(msg)
        charts, genres = app.fs.recv_info_from_backend_server()
        new_genres = []
        for genre in genres:
            new_genres.append(genre[0])
        return render_template('welcome.html', charts=charts, len=len(charts), genres=new_genres, length=len(new_genres))
    return redirect('/')


@app.route('/home_page/<string:chart_name>', methods=['POST', 'GET'])
def chart(chart_name):
    if "name" in app.fs.session:
        if request.method == 'POST':
            form_data = request.form
            comment = form_data.getlist('content')
            msg = "4" + str(len(chart_name)).zfill(2) + chart_name + str(len(app.fs.session["name"])).zfill(2) \
                  + app.fs.session["name"] + str(comment)
            app.fs.send_to_backend_server(msg)
            comment = (app.fs.session["name"], comment)
            app.fs.session["comments"].append(comment)
            print(app.fs.session["comments"])
            return render_template('chart.html', comments=app.fs.session["comments"],
                                   len=len(app.fs.session["comments"]), name=chart_name)
        else:
            msg = "3" + chart_name
            app.fs.send_to_backend_server(msg)
            data, comments = app.fs.recv_info_from_backend_server()
            comments = convert_to_list(comments)
            app.fs.session["comments"] = comments
            print(comments)
            create_file(chart_name, data)
            app.fs.session["file"] = chart_name + ".pdf"
            return render_template('chart.html', comments=comments,
                                   len=len(comments), name=chart_name)
    return redirect('/')


@app.route('/upload', methods=['POST', 'GET'])
def upload():
    if "name" in app.fs.session:
        if request.method == 'GET':
            msg = "a"
            app.fs.send_to_backend_server(msg)
            genres = app.fs.recv_info_from_backend_server()
            return render_template('upload.html', genres=genres, length=len(genres))
        # gets all the info from user
        name = request.form['name']
        genre = request.form['genre']
        add = request.form['add']
        file = request.files['file']
        # check that everything is here
        if not name:
            flash('Name is required!')
        elif not genre and not add:
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
            genre = genre[4: -5]
            creator = app.fs.session["name"]
            len_creator = str(len(creator)).zfill(2)
            len_data = str(len(data)).zfill(8)
            if not add:
                msg = "55" + str(len(name)).zfill(2) + name + str(len(genre)) + genre + len_creator + creator + len_data
            else:
                msg = "50" + str(len(name)).zfill(2) + name + str(len(add)) + add + len_creator + creator + len_data
            msg = bytes(msg.encode()) + data
            app.fs.send_to_backend_server(msg)
            return redirect('/home_page')
        return redirect('/upload')
    return redirect('/')


@app.route('/download/<path:path>')
def download_file(path):
    path = path + ".pdf"
    return send_file(path, as_attachment=True)


@app.route('/owner', methods=['GET'])
def owner():
    if "name" in app.fs.session:
        msg = "7" + str(len(app.fs.session["name"])).zfill(2) + app.fs.session["name"]
        app.fs.send_to_backend_server(msg)
        charts = app.fs.recv_info_from_backend_server()
        return render_template('owner.html', charts=charts, length=len(charts))
    return redirect('/')


@app.route('/delete/<string:chart>', methods=['GET'])
def delete(chart):
    if "name" in app.fs.session:
        msg = "8" + str(len(chart)).zfill(2) + chart
        app.fs.send_to_backend_server(msg)
        return redirect('/owner')
    return redirect('/')


@app.route('/leave')
def leave():
    app.fs.session.pop("file", None)
    app.fs.session.pop("name", None)
    return "BA-BAYY :)"


def create_file(name, data):
    name = name + '.pdf'
    file = open(name, 'ab')
    pickle.dump(data, file)
    file.close()


if __name__ == "__main__":
    # runs the website, with debug option
    app.run(debug=True, use_debugger=True, use_reloader=False, passthrough_errors=True, host="0.0.0.0")

    # webbrowser.open("http://192.168.0.156:5000")
