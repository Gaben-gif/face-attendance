from . import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    face_encoding = db.Column(db.PickleType, nullable=True)  # Nullable for admin/teacher if needed
    image_path = db.Column(db.String(200), nullable=True)    # Nullable for admin/teacher if needed
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(32), nullable=False, default='student')  # student, teacher, admin

    # For teachers: relationship to courses they teach
    taught_courses = db.relationship(
        'Course',
        backref='teacher',
        lazy='dynamic',
        cascade='all, delete-orphan',
        foreign_keys='Course.teacher_id'
    )

    # For students: relationship to their enrollments and attendance logs
    enrollments = db.relationship(
        'Enrollment',
        backref='student',
        lazy='dynamic',
        cascade='all, delete-orphan',
        foreign_keys='Enrollment.student_id'
    )

    attendance_logs = db.relationship(
        'AttendanceLog',
        backref='user',
        lazy='dynamic',
        cascade='all, delete-orphan',
        foreign_keys='AttendanceLog.user_id'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.name} ({self.role})>'

class Semester(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    courses = db.relationship(
        'Course',
        backref='semester',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Semester {self.name}>'

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey('semester.id'), nullable=False)

    enrollments = db.relationship(
        'Enrollment',
        backref='course',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    attendance_logs = db.relationship(
        'AttendanceLog',
        backref='course',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Course {self.code} - {self.name}>'

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', name='_student_course_uc'),)

    def __repr__(self):
        return f'<Enrollment student={self.student_id} course={self.course_id}>'

class AttendanceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AttendanceLog user={self.user_id} course={self.course_id} at {self.timestamp}>'