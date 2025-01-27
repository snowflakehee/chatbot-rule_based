from flask import Flask, render_template, request, session, redirect, url_for, jsonify, make_response
from flask_mysqldb import MySQL
from flask_cors import CORS
import re
import yaml
import jwt
import random
import json
import pickle
import numpy as np
import nltk
from nltk.stem import WordNetLemmatizer
from tensorflow.keras.models import load_model
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import logging

# Load database configuration from db.yaml
with open('db.yaml', 'r') as file:
    db = yaml.safe_load(file)

app = Flask(__name__)
CORS(app)  # Enable CORS for chatbot
app.secret_key = "abcd"
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']

mysql = MySQL(app)

# Load chatbot model and data
lemmatizer = WordNetLemmatizer()
intents = json.load(open('intents.json'))
words = pickle.load(open('model/words.pkl', 'rb'))
classes = pickle.load(open('model/classes.pkl', 'rb'))
model = load_model('model/chatbot_model.keras')

# Token required decorator for protected routes
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

# Chatbot utility functions
def clean_up_sentence(sentence):
    sentence_words = nltk.word_tokenize(sentence)
    sentence_words = [lemmatizer.lemmatize(word) for word in sentence_words]
    return sentence_words

def bag_of_words(sentence):
    sentence_words = clean_up_sentence(sentence)
    bag = [0] * len(words)
    for w in sentence_words:
        for i, word in enumerate(words):
            if word == w:
                bag[i] = 1
    return np.array(bag)

def predict_class(sentence):
    try:
        bow = bag_of_words(sentence)
        res = model.predict(np.array([bow]))[0]
        ERROR_THRESHOLD = 0.25
        results = [[i, r] for i, r in enumerate(res) if r > ERROR_THRESHOLD]
        results.sort(key=lambda x: x[1], reverse=True)
        return_list = []
        for r in results:
            return_list.append({'intent': classes[r[0]], 'probability': str(r[1])})
        print(f"Predicted classes: {return_list}")  # Debug print
        return return_list
    except Exception as e:
        print(f"Error in predict_class: {e}")  # Debug print
        return []

def get_response(intents_list, intents_json):
    if not intents_list:
        return "Sorry, I didn't understand that."

    tag = intents_list[0]['intent']
    list_of_intents = intents_json['intents']

    for i in list_of_intents:
        if i['tag'] == tag:
            result = random.choice(i['responses'])
            return result

    return "Sorry, I didn't understand that."

# Route for user registration
@app.route("/", methods=['GET'])
def home_page():
    return render_template('home.html')
# Password validation function
def validate_password(password):
    # Password requirements: minimum 8 characters, one uppercase, one lowercase, one digit, one special character
    password_regex = r"^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&()_+])[a-zA-Z0-9!@#$%^&()_+]{8,}$"
    if not re.match(password_regex, password):
        return False, "Password must be at least 8 characters long and include an uppercase letter, a lowercase letter, a number, and a special character."
    return True, "Password is strong."

@app.route("/index.html", methods=['GET', 'POST'])
def index():
    if request.method == "POST":
        userDetails = request.form
        name = userDetails['name']
        email = userDetails['email']
        password = userDetails['password']

        # Validate password strength
        is_valid, msg = validate_password(password)
        if not is_valid:
            return render_template('index.html', msg=msg)  # Return error if password is not valid
        
        hashed_password = generate_password_hash(password)
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(name, email, password) VALUES(%s, %s, %s)", (name, email, hashed_password))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('login'))
    
    return render_template('index.html')


# Route for user login
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

        if record and check_password_hash(record[3], password):
            token = jwt.encode({
                'user': record[1],
                'exp': datetime.utcnow() + timedelta(minutes=30)
            }, app.config['SECRET_KEY'], algorithm="HS256")
            # Set token and redirect to amigo.html
            resp = make_response(redirect(url_for('middle')))  
            resp.set_cookie('token', token, httponly=True)
            return resp
        else:
            msg = 'Incorrect email or password. Try again.'

    return render_template('amigo.html', msg=msg)

# Route for Amigo Chatbot (Protected)
@app.route('/amigo.html')
@token_required
def amigo():
    return render_template('amigo.html')


# Protected route - Home
@app.route('/home.html')
@token_required
def home():
    return render_template('home.html', name=session['user'])  # Display username instead of email

# Chatbot route (Protected by JWT token)
@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_input = request.json['message']
        print(f"Received message: {user_input}")  # Debug print
        ints = predict_class(user_input)
        print(f"Prediction result: {ints}")  # Debug print
        res = get_response(ints, intents)
        print(f"Response: {res}")  # Debug print
        return jsonify({'response': res})
    except Exception as e:
        print(f"Error: {e}")  # Debug print
        return jsonify({'response': str(e)})

# Route for logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('token', '', expires=0)  # Clear the JWT token
    return resp


@app.route('/quiz', methods=['GET'])
@token_required
def quiz():
    return render_template('quiz.html') 


 # Render the quiz page
 # Render the quiz page



@app.route('/middle', methods=['GET'])
@token_required  
def middle():
    return render_template('middle.html')



@app.route('/feedback', methods=['GET'])
@token_required
def feedback():
    return render_template('feedback.html')


@app.route('/test_db_connection')
def test_db_connection():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT DATABASE();")
        db_name = cur.fetchone()
        return f"Connected to database: {db_name}"
    except Exception as e:
        return f"Error: {e}", 500
    
@app.route('/test_config')
def test_config():
    return f"Host: {app.config['MYSQL_HOST']}, User: {app.config['MYSQL_USER']}, Database: {app.config['MYSQL_DB']}"


if __name__ == '__main__':
    app.config['SECRET_KEY'] = 'FXOJGu8-iBELAyU3'
    app.run(debug=True)