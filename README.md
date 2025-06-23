# Theft & Intruder Detection Web App

The proposed solution consists of the a web application where the the user is able to create an account to later sign in. The web application allows the user to choose his alert methods and view the live-stream. The system works by passing each frame of the live-stream to the to the deep learning
algorithm. The algorithm is able to perform live face recognition and object detection and classification. The detected objects are also tracked using an object-tracking algorithm. The user is alerted via
mail or Telegram message based on his choice, if an intruder is detected and an object has been stolen.
The system uses face recognition library by OpenCV to perform face detection and recognition while the object detection is performed using YOLOv8 model, which has been pre-trained on the COCO
(Common Objects in Context) dataset.

---

## Features

- Real-time face recognition using `dlib` + `face_recognition`
- Object detection and tracking with `YOLOv8` and `Supervision`
- Telegram & email alert system for emergency detection (e.g. weapons)
- User session management with Flask-Login
- Image logging and storage with timestamping
- SQLite database integration via SQLAlchemy and Flask-Migrate

---

## Installation

1. **Clone the repository**

```bash
git clone git@github.com:waseemahedoo/Theft-Detection-using-AI.git
cd 
```
2. **Create a virtual environment**
   
 ```bash
python3 -m venv venv
source venv/bin/activate
```
4. **Install all the requirements**

```bash
pip install -r requirements.txt
 ```
5. **Create a .env file**
   
```bash
SECRET_KEY=your_secret_key
SQLALCHEMY_DATABASE_URI=sqlite:///database.db
UPLOAD_FOLDER=uploads

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=465
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_email_password
MAIL_USE_TLS=False
MAIL_USE_SSL=True

PREDICTOR_PATH=models/shape_predictor_68_face_landmarks.dat
FACE_RECOG_MODEL_PATH=models/dlib_face_recognition_resnet_model_v1.dat

TELEGRAM_AUTH_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=-100123456789
TELEGRAM_GROUP_ID=Theft_detector

SENDER_EMAIL=your_email@gmail.com
RECEIVER_EMAIL=recipient_email@gmail.com
PHOTO_SAVE_DIR=photos
```
6. **Download Dlib and YOLOv8 Models**

Place the following files in the models/ folder:
```bash
shape_predictor_68_face_landmarks.dat
dlib_face_recognition_resnet_model_v1.dat
```
7. **Run app**
```bash
flask run
```
