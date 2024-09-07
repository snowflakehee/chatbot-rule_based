import os

# Create the directory if it doesn't exist
if not os.path.exists('model'):
    os.makedirs('model')

# Suppress TensorFlow logging (optional)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import random
import json
import pickle
import numpy as np
import nltk
from nltk.stem import WordNetLemmatizer
   # Ensure that 'punkt' is downloaded for tokenization
nltk.download('wordnet') # Download 'wordnet' for lemmatization
nltk.data.path.append('C:/Users/Lenovo/AppData/Roaming/nltk_data')
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Activation, Dropout
from tensorflow.keras.optimizers import SGD

lemmatizer = WordNetLemmatizer()

# Ensure the file name is correct ('intents.json' or 'intense.json')
intents = json.load(open('intents.json'))  # Adjust file name if needed

words = []
classes = []
documents = []
ignore_letters = ['?', '!', '.', ',']

# Processing the intents
for intent in intents['intents']:
    for pattern in intent['patterns']:
        word_list = nltk.word_tokenize(pattern)
        words.extend(word_list)
        documents.append((word_list, intent['tag']))
        if intent['tag'] not in classes:
            classes.append(intent['tag'])

# Lemmatize and sort the words
words = [lemmatizer.lemmatize(word.lower()) for word in words if word not in ignore_letters]
words = sorted(set(words))

# Sort classes
classes = sorted(set(classes))

# Save the words and classes for future use
pickle.dump(words, open('model/words.pkl', 'wb'))
pickle.dump(classes, open('model/classes.pkl', 'wb'))

# Preparing training data
training = []
output_empty = [0] * len(classes)

for document in documents:
    bag = []
    word_patterns = document[0]
    word_patterns = [lemmatizer.lemmatize(word.lower()) for word in word_patterns]

    for word in words:
        bag.append(1) if word in word_patterns else bag.append(0)

    output_row = list(output_empty)
    output_row[classes.index(document[1])] = 1
    training.append([bag, output_row])

# Shuffle and convert to NumPy array
random.shuffle(training)
training = np.array(training, dtype=object)

train_x = list(training[:, 0])
train_y = list(training[:, 1])

# Define the model
model = Sequential()
model.add(Dense(128, input_shape=(len(train_x[0]),), activation='relu'))
model.add(Dropout(0.5))
model.add(Dense(64, activation='relu'))
model.add(Dropout(0.5))
model.add(Dense(len(train_y[0]), activation='softmax'))

# Compile the model with SGD optimizer
sgd = SGD(learning_rate=0.01, momentum=0.9, nesterov=True)
model.compile(loss='categorical_crossentropy', optimizer=sgd, metrics=['accuracy'])

# Train the model
model.fit(np.array(train_x), np.array(train_y), epochs=200, batch_size=5, verbose=1)

# Save the trained model
model.save('model/chatbot_model.keras')

print("Model trained and saved successfully!")
