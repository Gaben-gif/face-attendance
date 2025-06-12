import os
import numpy as np
import cv2
import face_recognition
from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, request, abort, flash
from . import db
from datetime import datetime, timedelta
from app import login
from app.forms import SemesterForm, CourseForm, EnrollmentForm
from app.models import User, Semester, Course, Enrollment, AttendanceLog
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/index')
def index():
    return render_template('index.html')

@bp.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance_page():
    if current_user.role != 'student':
        abort(403)
    return render_template('attendance.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        role = request.form['role']
        image_file = request.files['image']

        # Save image
        if not image_file:
            return render_template('register.html', error="Image required")
        image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image_file.filename)
        image_file.save(image_path)

        # Encode face
        img = face_recognition.load_image_file(image_path)
        encodings = face_recognition.face_encodings(img)
        if len(encodings) != 1:
            os.remove(image_path)
            return render_template('register.html', error="Exactly one face must be visible in the image.")
        encoding = encodings[0]

        # Save user
        user = User(name=name, face_encoding=encoding, image_path=image_file.filename, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('main.login'))
    return render_template('register.html')

@bp.route('/api/register', methods=['POST'])
def register_user():
    data = request.form
    name = data.get('name')
    image_file = request.files['image']
    if not name or not image_file:
        return jsonify({'success': False, 'msg': 'Missing name or image.'}), 400

    # Save image
    filename = secure_filename(f"{name}_{datetime.utcnow().timestamp()}.jpg")
    img_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
    image_file.save(img_path)

    # Load image and generate encoding
    img = face_recognition.load_image_file(img_path)
    face_locations = face_recognition.face_locations(img)
    if len(face_locations) != 1:
        os.remove(img_path)
        return jsonify({'success': False, 'msg': 'No face or multiple faces detected.'}), 400
    encoding = face_recognition.face_encodings(img, face_locations)[0]

    # Save user
    user = User(name=name, face_encoding=encoding, image_path=filename)
    db.session.add(user)
    db.session.commit()
    return jsonify({'success': True, 'msg': 'Registration successful!'})

@bp.route('/api/mark_attendance', methods=['POST'])
def mark_attendance():
    image_file = request.files['image']
    if not image_file:
        return jsonify({'success': False, 'msg': 'Image missing'}), 400
    img = face_recognition.load_image_file(image_file)
    face_locations = face_recognition.face_locations(img)
    if len(face_locations) == 0:
        return jsonify({'success': False, 'msg': 'No face detected'}), 400
    encoding = face_recognition.face_encodings(img, face_locations)[0]

    # Compare with DB
    users = User.query.all()
    matches = []
    for user in users:
        match = face_recognition.compare_faces([np.array(user.face_encoding)], encoding, tolerance=0.6)[0]
        if match:
            matches.append(user)

    if not matches:
        return jsonify({'success': False, 'msg': 'No matching user found'}), 404

    user = matches[0]
    # Prevent duplicate attendance within 5 minutes
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)
    recent = AttendanceLog.query.filter_by(user_id=user.id).filter(AttendanceLog.timestamp > five_min_ago).first()
    if recent:
        return jsonify({'success': True, 'msg': f"Welcome back, {user.name}! Attendance already logged recently."})

    log = AttendanceLog(user_id=user.id)
    db.session.add(log)
    db.session.commit()
    return jsonify({'success': True, 'msg': f"Welcome, {user.name}! Attendance logged."})

@bp.route('/logs')
@login_required
def show_logs():
    if current_user.role not in ['teacher', 'admin']:
        abort(403)
    logs = AttendanceLog.query.order_by(AttendanceLog.timestamp.desc()).all()
    return render_template('logs.html', logs=logs)

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        user = User.query.filter_by(name=name).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('main.attendance_page'))  # or another start page
        else:
            error = "Invalid name or password"
    return render_template('login.html', error=error)


@bp.route('/users')
@login_required
def show_users():
    if current_user.role not in ['teacher', 'admin']:
        abort(403)
    users = User.query.all()
    return render_template('users.html', users=users)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@bp.route('/mylogs')
@login_required
def my_logs():
    logs = AttendanceLog.query.filter_by(user_id=current_user.id).all()
    return render_template('mylogs.html', logs=logs)

@bp.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    # Only admins can edit users
    if current_user.role != "admin":
        abort(403)

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')
        password = request.form.get('password')

        if name:
            user.name = name
        if role:
            user.role = role
        if password:
            user.set_password(password)
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('main.show_users'))

    return render_template('edit_user.html', user=user)


@bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != "admin":
        abort(403)
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot delete yourself.", "danger")
        return redirect(url_for('main.show_users'))
    AttendanceLog.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "success")
    return redirect(url_for('main.show_users'))

@bp.route('/semester/create', methods=['GET', 'POST'])
@login_required
def create_semester():
    if current_user.role != 'admin':
        flash('Only admins can create semesters.')
        return redirect(url_for('main.index'))
    form = SemesterForm()
    if form.validate_on_submit():
        semester = Semester(name=form.name.data)
        db.session.add(semester)
        db.session.commit()
        flash('Semester created!')
        return redirect(url_for('main.index'))
    return render_template('create_semester.html', form=form)

@bp.route('/course/create', methods=['GET', 'POST'])
@login_required
def create_course():
    if current_user.role not in ['admin', 'teacher']:
        flash('Only admins or teachers can create courses.')
        return redirect(url_for('main.index'))
    form = CourseForm()
    # Populate select fields
    form.teacher.choices = [(t.id, t.name) for t in User.query.filter_by(role='teacher').all()]
    form.semester.choices = [(s.id, s.name) for s in Semester.query.all()]
    if form.validate_on_submit():
        course = Course(
            name=form.name.data,
            code=form.code.data,
            teacher_id=form.teacher.data,
            semester_id=form.semester.data
        )
        db.session.add(course)
        db.session.commit()
        flash('Course created!')
        return redirect(url_for('main.index'))
    return render_template('create_course.html', form=form)

@bp.route('/enrollment/create', methods=['GET', 'POST'])
@login_required
def create_enrollment():
    if current_user.role not in ['admin', 'teacher']:
        flash('Only admins or teachers can enroll students.')
        return redirect(url_for('main.index'))
    form = EnrollmentForm()
    # Populate select fields
    form.student.choices = [(s.id, s.name) for s in User.query.filter_by(role='student').all()]
    form.course.choices = [(c.id, f"{c.code} - {c.name}") for c in Course.query.all()]
    if form.validate_on_submit():
        # Prevent duplicate enrollment
        exists = Enrollment.query.filter_by(student_id=form.student.data, course_id=form.course.data).first()
        if exists:
            flash('Student already enrolled in this course.')
        else:
            enrollment = Enrollment(
                student_id=form.student.data,
                course_id=form.course.data
            )
            db.session.add(enrollment)
            db.session.commit()
            flash('Student enrolled!')
        return redirect(url_for('main.index'))
    return render_template('create_enrollment.html', form=form)
