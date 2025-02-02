import sys
import io
import tensorflow as tf
from tensorflow.keras.models import load_model
import cv2
import numpy as np
import os
import logging

# Redirect stdout and stderr to handle encoding explicitly
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Setup logging
logging.basicConfig(filename='test_model.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the path to the model directory
model_directory = r'C:\Users\80\Documents\sem 7\4CP31-Project\SAS1.2\app\models'

def load_and_preprocess_image(image_path):
    """Load and preprocess the image."""
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Image at path {image_path} not found.")
    
    print(f"Image path: {image_path}")
    
    # Resize image to match model input
    image = cv2.resize(image, (100, 100))
    image = np.expand_dims(image, axis=0)  # Add batch dimension
    return image

def recognize_face(image_path, student_id):
    """Load model and make predictions."""
    model_path = os.path.join(model_directory, f"trained_model_{student_id}.h5")
    
    # Print debug info for model path
    print(f"Model path: {model_path}")
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Trained model not found at {model_path}. Please train the model first.")
    
    model = load_model(model_path)
    image = load_and_preprocess_image(image_path)
    
    try:
        # Predict
        predictions = model.predict(image)
        class_id = np.argmax(predictions[0])
        
        if class_id == 1:  # Assuming 1 is the class for the student
            return student_id
        else:
            return None
    except Exception as e:
        # Explicitly handle encoding for error messages
        error_message = f"Prediction error: {str(e)}"
        print(error_message.encode('utf-8').decode('utf-8'))
        logging.error(error_message, exc_info=True)
        raise e

def main():
    # Replace with the path to your test image and student ID
    test_image_path = r'C:\Users\80\Pictures\face_pics\WIN_20240721_23_42_32_Pro.jpg'
    
    student_id = '21CP071'
    
    print(f"Test image path: {test_image_path}")
    
    if not os.path.isfile(test_image_path):
        print(f"File not found: {test_image_path}")
    else:
        print(f"File found: {test_image_path}")
    
    try:
        recognized_id = recognize_face(test_image_path, student_id)
        if recognized_id:
            print(f"Face recognized as student ID: {recognized_id}")
        else:
            print("Face not recognized.")
    except Exception as e:
        logging.error("Error occurred", exc_info=True)
        print("An error occurred. Check the log file for details.")

if __name__ == "__main__":
    main()
