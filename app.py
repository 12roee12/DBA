import hashlib # for one-side-encryption (for passwords)
import os  # to move files
import shutil
import webbrowser  # for opening the website straight from here
from datetime import timedelta
from urllib.parse import urljoin  # for making the file be an url
from urllib.request import pathname2url
from flask import Flask, flash, render_template, request, session, url_for  # stuff for the website to work
from werkzeug.utils import redirect  # for the website to work
from Db_handler import Db_handler


app = Flask(__name__)
# set a secret key because I need to
app.config['SECRET_KEY'] = 'de36039d4efd74a5e51ab16869e554fc'
app.db = Db_handler()
app.permanent_session_lifetime = timedelta(minutes=10)


@app.route('/')
def index():
    # access to index page, where the user writes his username and password to see all the charts.
    return render_template('index.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    # this function handles the logging into the website.
    if request.method == 'GET':
        if 'name' in session:
            return redirect(url_for("home_page"))
        return render_template("index.html")
    if request.method == 'POST':
        session.permanent = True
        # getting the username and password, and making necessary changes.
        form_data = request.form
        name = str(form_data.getlist("username"))
        name = name[2:-2]
        if name != "":
            password = form_data.getlist("password")
            # encrypting the password.
            enc_password = hashlib.md5(str(password).encode()).hexdigest()
            # gets the password which belongs to the name to check if the password given is the same as that
            task = "SELECT * FROM customers WHERE name = %(name)s AND password = %(password)s"
            info = {'name': name, 'password': enc_password}
            data = app.db.request_get_where(task, info)

            if data is not None:
                session["name"] = name
                # the password is good, so the user can go to the charts
                return redirect(url_for("home_page"))
        # the username and/or the password are not good, so the user has to stay in this page
        flash('username or password are not correct')
        app.db.commit()
        return render_template("index.html")


@app.route('/sign_up', methods=['POST', 'GET'])
def go_to_sign_up():
    # sends the user to sign up page
    return render_template('signup.html')


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    # handles sign up page
    if request.method == 'GET':
        flash('got a GET method')
        return redirect('/')
    if request.method == 'POST':
        # get data that the user gave
        form_data = request.form
        name = str(form_data.getlist("username"))
        name = name[2:-2]
        password = form_data.getlist("password")
        password = password[0]
        re_right = form_data.getlist("re_right")
        re_right = re_right[0]
        # check if both passwords are the same
        if re_right != password:
            flash('the passwords are not the same.')
            return redirect('/sign_up')
        # the session is for the server to remember the client's name
        session["name"] = name
        # encrypting the password
        enc_password = hashlib.md5(str(password).encode()).hexdigest()
        # adding new info to the database, and sending the user to the charts page
        task = "INSERT INTO customers (name, password) VALUES (%(name)s, %(password)s)"
        info = {'name': name, 'password': enc_password}
        app.db.request_insert(task, info)
        return redirect(url_for("home_page"))


@app.route("/home_page", methods=['POST', 'GET'])
def home_page():
    if 'name' in session:
        # means that the server remembers the client
        charts = app.db.request_get_all('SELECT * FROM charts')
        app.db.commit()
        if request.method == 'POST':
            form_data = request.form
            genre = form_data.getlist('genre')
            task = "SELECT * FROM charts WHERE genre = %(genre)s"
            info = {'genre': genre}
            charts = app.db.request_get_where(task, info)
            app.db.commit()
            return render_template('welcome.html', charts=charts, len=len(charts))
        return render_template('welcome.html', charts=charts, len=len(charts))
    else:
        # in most cases, it means that the client tried to go inside the website without entering name and password
        return redirect('/')


@app.route('/data/<string:chart_name>')
def chart(chart_name):
    # send the chart requested to see it
    if 'name' not in session:
        return redirect('/')
    path = str(get_chart(chart_name))
    chart_name = path.split('\\')[-1]
    chart_name = chart_name.split('.')[0]
    app.db.cursor.execute('SELECT * FROM ' + chart_name)
    comments = app.db.cursor.fetchall()
    chart_name = chart_name.replace("_", " ")
    return render_template('chart.html', path=path, comments=comments, len=len(comments), name=chart_name)


def path2url(path):
    # makes the file be an url
    return urljoin('file:', pathname2url(path))


def get_chart(chart_name):
    # finds the chart to show
    chart = chart_name + '.pdf'
    return find_files(chart, 'files')


@app.route('/upload', methods=('GET', 'POST'))
def upload():
    if 'name' not in session:
        return redirect('/')
    # handles uploading charts to website
    if request.method == 'POST':
        # gets all the info from user
        name = request.form['name']
        genre = request.form['genre']
        file = request.form['file']
        # check that everything is here
        if not name:
            flash('Name is required!')
        elif not genre:
            flash('Genre is required!')
        elif not file:
            flash('Chart is required!')
        else:
            # add the info to the database
            task = 'INSERT INTO charts (name, genre, likes) VALUES (%(name)s, %(genre)s, %(likes)s)'
            info = {'name': name, 'genre': genre, 'likes': 0}
            app.db.request_insert(task, info)
            charts = app.db.request_get_all('SELECT * FROM charts')
            app.db.commit()
            # add the file to 'C:\\Users\\user\\PycharmProjects\\website\\files\\', and sends back to welcome page
            path = find_files(file, 'C:\\')
            if path is None:
                flash(
                    "Something went wrong. The server wasn't able to find your file. Make sure that your file is in C:/")
            path = path.replace("'", "")
            path = path.replace(" ", "_")
            args = ["name", "comment"]
            app.db.create_table(path, args)
            shutil.move(path, create_path(name))
            flash('Thank You :)')
            return render_template('welcome.html', charts=charts, len=len(charts))

    return render_template('upload.html')


app.route('/<string:chart_name>', methods=['POST', 'GET'])
def handle_message(chart_name):
    if request.method == 'post':
        form_data = request.form
        message = form_data.getlist('content')
        name = session["name"]
        task = f'INSERT INTO {chart_name} (name, content) VALUES (%, %)', (name, message)
        app.db.cursor.execute(task)
        return redirect(url_for(chart(chart_name)))
    else:
        return redirect(url_for(chart(chart_name)))


def create_path(name):
    return 'C:\\Users\\user\\PycharmProjects\\website\\app\\files\\' + name + '.pdf'


def find_files(filename, search_path):
    # search the file in the computer
    result = []
    # Walking top-down from the root
    for root, dir, files in os.walk(search_path):
        if filename in files:
            result.append(os.path.join(root, filename))
            return result[0]
    return None


@app.route('/leave')
def leave():
    # gets the info out of the session so the user won't be able to connect without username and password
    session.pop('name', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    # runs the website, with debug option
    app.run(debug=True, use_debugger=True, use_reloader=False, passthrough_errors=True)
    webbrowser.open("http://127.0.0.1:5000")
