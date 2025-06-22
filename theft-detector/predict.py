from flask import Blueprint, request, jsonify, current_app, render_template, session
from flask_mail import Mail, Message
from flask_login import current_user
from .models import Images, User
from . import db

import base64
import requests
from PIL import Image
import io
import cv2
import numpy as np
import face_recognition
import dlib
from ultralytics import YOLO
import supervision as sv
from datetime import datetime
import os
from dotenv import load_dotenv
import telepot

# Load environment variables
load_dotenv()

predictor_path = os.getenv('PREDICTOR_PATH')
face_rec_model_path = os.getenv('FACE_RECOG_MODEL_PATH')

assert predictor_path and face_rec_model_path, "Model paths must be set in .env"

# Load Dlib models
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(predictor_path)
face_recognition_model = dlib.face_recognition_model_v1(face_rec_model_path)

tele_auth_token = os.getenv('TELEGRAM_AUTH_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')
tel_group_id = os.getenv('TELEGRAM_GROUP_ID')
bot = telepot.Bot(tele_auth_token)

sender_email = os.getenv('SENDER_EMAIL')
receiver_email = os.getenv('RECEIVER_EMAIL')

photo_save_dir = os.getenv("PHOTO_SAVE_DIR", "photos")
os.makedirs(photo_save_dir, exist_ok=True)

# Load YOLO model
def load_model():
    model = YOLO("yolov8l.pt")
    model.fuse()
    return model

model = load_model()
CLASS_NAMES_DICT = model.model.names
CLASS_ID = [67]  

LINE_START = sv.Point(200, 0)
LINE_END = sv.Point(200, 720)
line_counter = sv.LineZone(start=LINE_START, end=LINE_END)
line_annotator = sv.LineZoneAnnotator(thickness=2, text_thickness=1, text_scale=0.5)
box_annotator = sv.BoxAnnotator(thickness=2, text_thickness=1, text_scale=0.5)

predict = Blueprint('predict', __name__)

@predict.route('/', methods=['GET'])
def home_page():
    return render_template("home.html", user=current_user)

def get_image():
    if "user_photo_encoding" not in session:
        assert "email" in session, "User session not found"
        user = User.query.filter_by(email=session["email"]).first()
        face_image = face_recognition.load_image_file(user.user_photo_path)
        face_encoding = face_recognition.face_encodings(face_image)[0]
        session["user_photo_encoding"] = face_encoding.tolist()
    return session["user_photo_encoding"]

@predict.route('/check-image', methods=['POST'])
def check_image():
    with current_app.app_context():
        mail = Mail(current_app)

    session_face_encoding = np.array(get_image())
    img_string = request.form['image']
    telegram = request.form['telegram']
    email = request.form['email']

    img_data = base64.b64decode(img_string.split(',')[1])
    frame = Image.open(io.BytesIO(img_data))
    model_frame = np.asarray(frame)
    rgb_frame = cv2.cvtColor(model_frame, cv2.COLOR_BGR2RGB)
    frame = np.ascontiguousarray(rgb_frame)

    face_locations = face_recognition.face_locations(rgb_frame)
    face_locations_dlib = [dlib.rectangle(left=x[3], top=x[0], right=x[1], bottom=x[2]) for x in face_locations]
    face_landmarks = [predictor(rgb_frame, face_location) for face_location in face_locations_dlib]
    face_encodings = [np.array(face_recognition_model.compute_face_descriptor(rgb_frame, landmark, 1)) for landmark in face_landmarks]

    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        matches = face_recognition.compare_faces([session_face_encoding], face_encoding)
        if matches[0]:
            return jsonify({'matches': "true", 'left': left, 'top': top, 'right': right, 'bottom': bottom}), 200

        result = model.track(frame, show=False, stream=False)
        frame = result[0].orig_img
        detections = sv.Detections.from_yolov8(result[0])

        if result[0].boxes.id is not None:
            detections.tracker_id = result[0].boxes.id.cpu().numpy().astype(int)

        detections = detections[(detections.class_id != 60) & (detections.class_id != 0)]
        labels = [
            f"{tracker_id} {model.model.names[class_id]} {confidence:0.2f}"
            for _, confidence, class_id, tracker_id in detections
        ]

        detections_dict = [
            {
                'xyxy': list(map(float, box)),
                'confidence': float(detections.confidence[i]),
                'class_id': int(detections.class_id[i]),
                'label': labels[i]
            }
            for i, box in enumerate(detections.xyxy)
        ]

        frame = box_annotator.annotate(scene=frame, detections=detections, labels=labels)
        line_counter.trigger(detections=detections)
        line_annotator.annotate(frame=frame, line_counter=line_counter)

        curr_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        photo_url = os.path.join(photo_save_dir, f"{curr_datetime}.jpg")
        cv2.imwrite(photo_url, frame)

        for detection in detections_dict:
            if detection['label'].lower().find('knife') != -1:
                if telegram == "true":
                    send_msg_on_telegram("EMERGENCY: Weapon detected", tele_auth_token, tel_group_id)
                    send_photo(bot, chat_id, photo_url)
                if email == "true":
                    send_email(mail, "Emergency: Weapon Detected", photo_url)

        category = "Theft" if line_counter.out_count > 0 else "Intruder"
        data = f"{category} detected"
        db.session.add(Images(filepath=photo_url, category=category))
        db.session.commit()

        if telegram == "true":
            send_msg_on_telegram(data, tele_auth_token, tel_group_id)
            send_photo(bot, chat_id, photo_url)

        if email == "true":
            send_email(mail, data, photo_url)

        return jsonify({
            'matches': "false",
            'left': left,
            'top': top,
            'right': right,
            'bottom': bottom,
            'detections': detections_dict,
            'out': line_counter.out_count,
            'data': data
        }), 200

def send_msg_on_telegram(msg, token, group_id):
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id=@{group_id}&text={msg}"
    response = requests.get(url)
    if response.status_code == 200:
        current_app.logger.info("Telegram message sent")
    else:
        current_app.logger.error("Failed to send Telegram message")

def send_photo(bot, chat_id, photo_url):
    try:
        with open(photo_url, 'rb') as photo:
            bot.sendPhoto(chat_id, photo)
    except Exception as e:
        current_app.logger.error(f"Failed to send photo: {e}")

def send_email(mail, subject, photo_path):
    try:
        msg = Message(subject, sender=sender_email, recipients=[receiver_email])
        msg.body = subject
        with current_app.open_resource(photo_path) as fp:
            msg.attach("alert.jpg", "image/jpg", fp.read())
        mail.send(msg)
        current_app.logger.info("Email sent")
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {e}")
