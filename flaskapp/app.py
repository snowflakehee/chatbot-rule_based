from flask import Flask, render_template, request, session, redirect, url_for, jsonify, make_response
from flask_mysqldb import MySQL
import yaml
import jwt
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import logging

with open('db.yaml', 'r') as file:
    db = yaml.safe_load(file)

app = Flask(__name__)
app.secret_key = "abcd"
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']

mysql = MySQL(app)

# Token required decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('token')
        if not token:
            return redirect(url_for('login'))

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            session['user'] = data['user']  # Store username in session
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 403
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 403

        return f(*args, **kwargs)
    return decorated

@app.route("/", methods=['GET', 'POST'])
@app.route("/index.html", methods=['GET', 'POST'])
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

        if record and check_password_hash(record[2], password):
            # Generate JWT token with username
            token = jwt.encode({
                'user': record[0],  # Use the username instead of email
                'exp': datetime.utcnow() + timedelta(minutes=30)
            }, app.config['SECRET_KEY'], algorithm="HS256")

            # Debug: Print token to console/log for verification
            logging.debug(f"JWT Token generated: {token}")

            # Store token in a cookie
            resp = make_response(redirect(url_for('home')))
            resp.set_cookie('token', token, httponly=True)
            return resp
        else:
            msg = 'Incorrect email or password. Try again.'

    return render_template('login.html', msg=msg)

# Protected route (requires valid JWT token)
@app.route('/home.html')
@token_required
def home():
    return render_template('home.html', name=session['user'])  # Return username instead of email

@app.route('/chat', methods=['POST'])
@token_required
def chat():
    data = request.get_json()
    message = data.get('message')
    response = f"Chatbot response to: {message}"
    return jsonify({'response': response})

@app.route('/logout')
def logout():
    session.pop('user', None)
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('token', '', expires=0)  # Clear the JWT token
    return resp

if __name__ == "__main__":
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.run(debug=True)
