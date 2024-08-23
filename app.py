import cv2
import numpy as np
from flask import Flask, request, jsonify, send_file, render_template
from io import BytesIO
from ultralytics import YOLO
from flask_cors import CORS, cross_origin
import json

app = Flask(__name__)
CORS(app)

class SmartIDDetectionPipeline:
    def __init__(self, id_card_model_path, aadhaar_pid_model_path, pan_pid_model_path, voter_pid_model_path, passport_pid_model_path):
        self.id_card_model = YOLO(id_card_model_path)
        self.aadhaar_pid_model = YOLO(aadhaar_pid_model_path)
        self.pan_pid_model = YOLO(pan_pid_model_path)
        self.voter_pid_model = YOLO(voter_pid_model_path)
        self.passport_pid_model = YOLO(passport_pid_model_path)

    def detect_card_type(self, image):
        results = self.id_card_model(image, conf=0.25)[0]
        detections = [
            [*r[:4], self.id_card_model.names[int(r[5])]]
            for r in results.boxes.data.tolist()
        ]
        return detections

    def extract_pids(self, image, model):
        results = model(image, conf=0.25)[0]
        detections = [
            [*r[:4], model.names[int(r[5])]]
            for r in results.boxes.data.tolist()
        ]
        return detections

    def process_image(self, image):
        card_type_detections = self.detect_card_type(image)

        card_types = {
            'aadhaar': ['aadhaar_front', 'back_aadhar', 'long_aadhar_front', 'long_aadhar_back'],
            'pan': ['Pan-Card'],
            'voter': ['card_voterid_1_back', 'card_voterid_1_front', 'card_voterid_2_back', 'card_voterid_2_front'],
            'passport': ['passport_back', 'passport_front']
        }

        detected_card_type = None
        for card_type, labels in card_types.items():
            if any(det[4] in labels for det in card_type_detections):
                detected_card_type = card_type
                break

        if detected_card_type == 'aadhaar':
            pid_detections = self.extract_pids(image, self.aadhaar_pid_model)
        elif detected_card_type == 'pan':
            pid_detections = self.extract_pids(image, self.pan_pid_model)
        elif detected_card_type == 'voter':
            pid_detections = self.extract_pids(image, self.voter_pid_model)
        elif detected_card_type == 'passport':
            pid_detections = self.extract_pids(image, self.passport_pid_model)
        else:
            pid_detections = []
            detected_card_type = 'unknown'

        return detected_card_type, card_type_detections, pid_detections

    def visualize_results(self, image, card_type_detections, pid_detections, selected_labels):
        for det in card_type_detections:
            x1, y1, x2, y2 = map(int, det[:4])
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 3)
            cv2.putText(image, det[4], (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

        for det in pid_detections:
            x1, y1, x2, y2 = map(int, det[:4])
            label = det[4]
            if label in selected_labels:
                image[y1:y2, x1:x2] = (0, 0, 0)

        return image

# Initialize your pipeline
pipeline = SmartIDDetectionPipeline(
    id_card_model_path="model_weights/id_card_detection.pt",
    aadhaar_pid_model_path="model_weights/aadhaar_pid_detection.pt",
    pan_pid_model_path="model_weights/pan_pid_detection.pt",
    voter_pid_model_path="model_weights/voter_pid_detection.pt",
    passport_pid_model_path="model_weights/passport_pid_detection.pt"
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/detect_card_type', methods=['POST'])
@cross_origin()
def detect_card_type():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400

    image = request.files['image'].read()
    nparr = np.frombuffer(image, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    card_type, _, _ = pipeline.process_image(img)

    return jsonify({"card_type": card_type})

def resize_image(image, max_width=800, max_height=600):
    height, width = image.shape[:2]
    if width > max_width or height > max_height:
        scaling_factor = min(max_width / width, max_height / height)
        new_size = (int(width * scaling_factor), int(height * scaling_factor))
        image = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
    return image

@app.route('/detect_pids', methods=['POST'])
@cross_origin()
def detect_pids():
    if 'image' not in request.files or 'card_type' not in request.form:
        return jsonify({"error": "Image and card type are required"}), 400

    image = request.files['image'].read()
    nparr = np.frombuffer(image, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    card_type = request.form['card_type']

    selected_labels = json.loads(request.form.get('labels', '[]'))

    all_labels = {
        'aadhaar': ['aadhaar_no', 'aadhaar_dob', 'aadhaar_gender', 'aadhaar_address', 'aadhaar_holder_name',
                    'aadhaar_localname', 'aadhaar_new', 'aadhaar_addressLocal'],
        'pan': ['pan_num', 'dob', 'father', 'name'],
        'voter': ['Relation_localname', 'address', 'age', 'date_of_issue', 'dob', 'elector_name', 'gender', 'local_address', 'localname', 'photo', 'place', 'relation_name', 'voter_id_no'],
        'passport': ['DOB', 'File_no', 'Surname', 'address', 'country_code', 'date_of_expiry', 'date_of_issue', 'details', 'father_name', 'mother_name', 'name', 'nationality', 'old_passport_details', 'passport_no', 'photo', 'place_of_birth', 'place_of_issue', 'sex', 'sign', 'spouse_name', 'type']
    }

    if card_type not in all_labels:
        return jsonify({"error": "Invalid card type"}), 400

    if not selected_labels:
        selected_labels = all_labels[card_type]

    _, _, pid_detections = pipeline.process_image(img)
    visualized_image = pipeline.visualize_results(img, [], pid_detections, selected_labels)
    visualized_image = resize_image(visualized_image)

    is_success, buffer = cv2.imencode(".jpg", visualized_image)
    io_buf = BytesIO(buffer)

    return send_file(io_buf, mimetype='image/jpeg')

if __name__ == '__main__':
    app.run(debug=True)