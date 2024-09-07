from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import json
import pickle
import numpy as np
import nltk
from nltk.stem import WordNetLemmatizer
from tensorflow.keras.models import load_model

app = Flask(__name__)
CORS(app)  # Enable CORS

lemmatizer = WordNetLemmatizer()
intents = json.load(open('intents.json'))
words = pickle.load(open('model/words.pkl', 'rb'))
classes = pickle.load(open('model/classes.pkl', 'rb'))
model = load_model('model/chatbot_model.keras')

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

if __name__ == '__main__':
    app.run(port=5000)
