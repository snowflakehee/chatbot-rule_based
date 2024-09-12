from flask import Flask, render_template, request, session, redirect, url_for
from flask_mysqldb import MySQL
import yaml
from werkzeug.security import generate_password_hash, check_password_hash

with open('db.yaml', 'r') as file:
    db = yaml.safe_load(file)

app = Flask(__name__)
app.secret_key = "abcd"
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']

mysql = MySQL(app)

@app.route("/home.html")
def home():
    if 'loggedin' in session:
        return render_template('home.html', name=session['name'])
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@app.route("/index.html",methods=['GET','POST'])
def index():
    if request.method == "POST":
        userDetails = request.form
        name = userDetails['name']
        email = userDetails['email']
        password = generate_password_hash(userDetails['password'])
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(name, email, password) VALUES(%s, %s, %s)", (name, email, password))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('login'))
    
    return render_template('index.html')
@app.route('/login.html', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        record = cur.fetchone()
        cur.close()
        
        if record and check_password_hash(record[2], password) :
            session['loggedin'] = True
            session['name'] = record[0]
            return redirect(url_for('home'))
        else:
            msg = 'Incorrect email or password. Try again.'
    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    session.pop("loggedin",None)
    session.pop("username",None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
