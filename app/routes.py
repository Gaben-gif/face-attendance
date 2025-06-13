import os
import numpy as np
import cv2
import face_recognition
from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, abort, flash
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

        # Collect all uploaded face images
        face_images = []
        for i in range(5):  # Adjust if you change maxCaptures
            file = request.files.get(f'face_image_{i}')
            if file:
                face_images.append(file)

        if len(face_images) < 5:
            return render_template('register.html', error="Please capture all face images.")

        encodings = []
        for idx, img_file in enumerate(face_images):
            img = face_recognition.load_image_file(img_file)
            face_locations = face_recognition.face_locations(img)
            print(f"Image {idx+1}: Detected {len(face_locations)} faces")
            if len(face_locations) < 1:
                return render_template('register.html', error=f"Image {idx+1}: No face detected. Please try again.")
            elif len(face_locations) > 1:
                return render_template('register.html', error=f"Image {idx+1}: Multiple faces detected. Only one person should be visible.")
            encoding = face_recognition.face_encodings(img, face_locations)[0]
            encodings.append(encoding)

        # Store encodings as a list (using PickleType in your model)
        user = User(name=name, role=role)
        user.set_password(password)
        user.face_encoding = encodings  # PickleType can store a list
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('main.login'))

    return render_template('register.html')


@bp.route('/api/mark_attendance', methods=['POST'])
@login_required
def mark_attendance():
    image_file = request.files.get('image')
    if not image_file:
        return jsonify({'success': False, 'msg': 'No image provided.'}), 400

    img = face_recognition.load_image_file(image_file)
    face_locations = face_recognition.face_locations(img)
    if len(face_locations) != 1:
        return jsonify({'success': False, 'msg': 'No face or multiple faces detected.'}), 400
    encoding = face_recognition.face_encodings(img, face_locations)[0]

    # Compare with all users
    users = User.query.all()
    for user in users:
        if user.face_encoding is not None:
            stored_encoding = np.array(user.face_encoding)
            match = face_recognition.compare_faces([stored_encoding], encoding, tolerance=0.6)[0]
            if match:
                # Mark attendance logic here
                return jsonify({'success': True, 'msg': f'Attendance marked for {user.name}.'})
    return jsonify({'success': False, 'msg': 'Face not recognized.'}), 401

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
            # Redirect based on user role
            if user.role == 'admin':
                return redirect(url_for('main.admin_dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('main.teacher_dashboard'))
            elif user.role == 'student':
                return redirect(url_for('main.student_dashboard'))
            else:
                return redirect(url_for('main.attendance_page'))  # fallback
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
    #form.semester.choices = [(s.id, s.name) for s in Semester.query.all()]
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

@bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@bp.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    return render_template('teacher_dashboard.html')

@bp.route('/student/dashboard')
@login_required
def student_dashboard():
    return render_template('student_dashboard.html')

@bp.route('/api/login_face', methods=['POST'])
def login_face():
    name = request.form.get('name')
    image_file = request.files.get('image')
    user = User.query.filter_by(name=name).first()
    if not user or not user.face_encoding:
        return jsonify({'success': False, 'msg': 'User not found or no face encoding.'}), 404

    img = face_recognition.load_image_file(image_file)
    face_locations = face_recognition.face_locations(img)
    if len(face_locations) != 1:
        return jsonify({'success': False, 'msg': 'No face or multiple faces detected.'}), 400
    encoding = face_recognition.face_encodings(img, face_locations)[0]

    # Compare against all stored encodings (face_encoding is a list)
    import numpy as np
    matches = face_recognition.compare_faces([np.array(e) for e in user.face_encoding], encoding, tolerance=0.6)
    if any(matches):
        login_user(user)
        return jsonify({'success': True, 'msg': 'Login successful!', 'role': user.role})
    else:
        return jsonify({'success': False, 'msg': 'Face does not match.'}), 401