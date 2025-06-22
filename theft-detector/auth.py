import os
import face_recognition
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, current_app
from werkzeug.utils import secure_filename

from .models import User
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user

auth = Blueprint('auth', __name__)
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user:
            if check_password_hash(user.password, password):
                flash('Logged in successfully!', category='success')
                login_user(user, remember=True)
                session["email"] = user.email
                return redirect(url_for('views.home'))

            else:
                flash('Incorrect password', category='error')
        else:
            flash('Email does not exist', category='error')

    return render_template("login.html", user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    # print("user logged out")
    # session.pop('user_photo_encoding', None)
    # session.pop('first_name', None)
    return redirect(url_for('auth.login'))

@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        if 'file' not in request.files:
            flash('No file part')
        file = request.files['file']
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists', category='error')
        if len(email) < 4:
            flash('Email must be greater than 3 characters', category='error')
        elif len(first_name) < 2:
            flash('First Name must be greater than 1 characters', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match', category='error')
        elif len(password1) < 7:
            flash('Password must be at least 7characters', category='error')
        else:
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                temp_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], "temp_" + filename)

                # Save the file temporarily to read its face encodings
                file.save(temp_filepath)

                face_image = face_recognition.load_image_file(file)
                face_locations = face_recognition.face_locations(face_image)
                if len(face_locations) == 0:
                    flash("No face detected in the image", category='error')
                    os.remove(temp_filepath)
                else:
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    # Rename or move the temp file to the intended location
                    os.rename(temp_filepath, filepath)
                    new_user = User(email=email, first_name=first_name, user_photo_path=filepath, password=generate_password_hash(password1, method='sha256'))
                    db.session.add(new_user)
                    db.session.commit()
                    login_user(new_user, remember=False)

                    flash('Account created!', category='success')
                    return redirect(url_for('views.home'))

    return render_template("sign_up.html", user=current_user)