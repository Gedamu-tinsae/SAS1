import sys
import io
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Input
import numpy as np
import os
import cv2
import base64
from io import BytesIO
from PIL import Image
import logging
from flask import Blueprint, request, jsonify, current_app, flash, redirect, url_for, render_template
from werkzeug.utils import secure_filename
from . import db
from .models import AttendanceRecord, User

# Redirect stdout and stderr to handle encoding explicitly
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler()])

# Define the path to the model directory
model_directory = r'C:\Users\80\Documents\sem 7\4CP31-Project\SAS1.3\app\models'
if not os.path.exists(model_directory):
    os.makedirs(model_directory)

def create_cnn_model():
    model = Sequential([
        Input(shape=(100, 100, 3)),  # Specify the input shape here
        Conv2D(32, (3, 3), activation='relu'),
        MaxPooling2D((2, 2)),
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D((2, 2)),
        Conv2D(64, (3, 3), activation='relu'),
        Flatten(),
        Dense(64, activation='relu'),
        Dense(2, activation='softmax')  # Assuming binary classification (e.g., known vs unknown)
    ])
    
    model.compile(optimizer='adam',
                  loss='sparse_categorical_crossentropy',
                  metrics=['accuracy'])
    return model

def train_model(student_id, images):
    # Preprocess images
    processed_images = []
    labels = []
    for image in images:
        image = cv2.resize(image, (100, 100))  # Resize images to match input shape
        processed_images.append(image)
        labels.append(1)  # Label all images with the same ID

    processed_images = np.array(processed_images)
    labels = np.array(labels)

    model = create_cnn_model()

    model_path = os.path.join(model_directory, f"trained_model_{student_id}.h5")
    logging.debug(f"Training and saving model with ID: {student_id}")
    try:
        logging.info("Training model...")
        model.fit(processed_images, labels, epochs=5)
        model.save(model_path)
        logging.info(f"Model saved to {model_path}")
        return True
    except Exception as e:
        error_message = f"Error training model for student ID {student_id}: {str(e)}"
        logging.error(error_message, exc_info=True)
        return False


def load_and_preprocess_image(image_data):
    """Load and preprocess the image from base64 data."""
    try:
        # Decode base64 image data
        image_data = image_data.split(',')[1]  # Skip the metadata part
        image = base64.b64decode(image_data)
        image = Image.open(BytesIO(image))
        image = np.array(image)
        
        # Convert RGB to BGR (OpenCV format)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        image = cv2.resize(image, (100, 100))
        image = np.expand_dims(image, axis=0)  # Add batch dimension
        return image
    except Exception as e:
        logging.error(f"Error during image preprocessing: {str(e)}", exc_info=True)
        raise e

def recognize_face(image_data, student_id):
    """Load model and make predictions."""
    model_path = os.path.join(model_directory, f"trained_model_{student_id}.h5")
    logging.debug(f"Attempting to load model from: {model_path}")
    if not os.path.exists(model_path):
        logging.error(f"Trained model not found at {model_path}. Please train the model first.")
        return None

    model = load_model(model_path)
    image = load_and_preprocess_image(image_data)
    
    try:
        # Predict
        predictions = model.predict(image)
        class_id = np.argmax(predictions[0])
        
        if class_id == 1:  # Assuming 1 is the class for the student
            return student_id
        else:
            return None
    except Exception as e:
        error_message = f"Prediction error: {str(e)}"
        logging.error(error_message, exc_info=True)
        raise e

