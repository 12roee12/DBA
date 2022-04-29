import sqlite3
from flask import Flask, flash, render_template, json, request, send_file
import mysql.connector
import webbrowser
from werkzeug.exceptions import abort
from werkzeug.utils import redirect

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

@app.route('/')
def index():
    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="first_db"
    )
    conn = mydb.cursor()
    conn.execute('SELECT * FROM customers')
    charts = conn.fetchall()
    mydb.commit()
    return render_template('index.html', charts=charts)

@app.route('/data', methods=['POST', 'GET'])
def data():
    if request.method == 'GET':
        return "got a GET method"
    if request.method == 'POST':
        form_data = request.form
        name = str(form_data.getlist("username"))
        name = name[2:-2]
        password = form_data.getlist("password")
        password = password[0]

        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="1234",
            database="first_db"
        )
        cursor = mydb.cursor()
        cursor.execute("SELECT * FROM customers WHERE name = %s", (str(name), ))
        data = cursor.fetchall()
        for x in data:
            for i in x:
                if i == password:
                    cursor.execute('SELECT * FROM charts')
                    charts = cursor.fetchall()
                    return render_template('welcome.html', len = len(charts), charts=charts)
        flash('username or password are not correct')
        mydb.commit()
        return redirect('/')

@app.route('/sign_up', methods=['POST', 'GET'])
def go_to_sign_up():
    return render_template('signup.html')

@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'GET':
        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="1234",
            database="first_db"
        )
        cursor = mydb.cursor()
        cursor.execute("SELECT * FROM charts")
        charts = cursor.fetchall()
        mydb.commit()
        return render_template('welcome.html', charts=charts)
    if request.method == 'POST':
        form_data = request.form
        name = str(form_data.getlist("username"))
        name = name[2:-2]
        password = form_data.getlist("password")
        password = password[0]
        re_right = form_data.getlist("re_right")
        re_right = re_right[0]
        if re_right != password:
            flash('the passwords are not the same.')
            return redirect('/sign_up')

        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="1234",
            database="first_db"
        )
        cursor = mydb.cursor()
        cursor.execute("INSERT INTO customers (name, password) VALUES (%s, %s)", (str(name), str(password)))
        mydb.commit()
        return render_template('/welcome.html')

@app.route('/x')
def welcome():
    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="first_db"
    )
    cursor = mydb.cursor()
    cursor.execute("SELECT * FROM charts")
    charts = cursor.fetchall()
    mydb.commit()
    return render_template('welcome.html', charts=charts)

@app.route('/data/<int:chart_id>')
def chart(chart_id):
    chart = get_chart(chart_id)
    return send_file(chart)

def get_chart(chart_id):
    f = open("files.txt", "r")
    line = f.readlines()[chart_id-1]
    return line


@app.route('/return-file')
def return_file():
    return send_file('C:\cyber\c.pdf')

@app.route('/Upload')
def go_to_upload():
    return render_template('upload.html')

@app.route('/upload')
def upload():
    form_data = request.form
    chart_name = form_data.getlist("chart_name")
    chart_name = chart_name[2:-2]
    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="first_db"
    )
    cursor = mydb.cursor()
    cursor.execute("INSERT INTO charts (name) VALUES (%s)", (str(chart_name)))
    flash('Your chart has been inserted into our database, and now everyone can see it. Thank you for your service! :)')
    mydb.commit()
    return render_template('welcome.html')

if __name__ == '__main__':
    app.run(debug=True, use_debugger=True, use_reloader=False, passthrough_errors=True)
    webbrowser.open("http://127.0.0.1:5000")