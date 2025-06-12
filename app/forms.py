from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired
from app.models import User, Semester, Course

class SemesterForm(FlaskForm):
    name = StringField('Semester Name', validators=[DataRequired()])
    submit = SubmitField('Create Semester')

class CourseForm(FlaskForm):
    name = StringField('Course Name', validators=[DataRequired()])
    code = StringField('Course Code', validators=[DataRequired()])
    teacher = SelectField('Teacher', coerce=int, validators=[DataRequired()])
    semester = SelectField(
        'Semester',
        choices=[(1, 'Semester 1'), (2, 'Semester 2')],
        coerce=int,
        validators=[DataRequired()]
    )
    submit = SubmitField('Create Course')

class EnrollmentForm(FlaskForm):
    student = SelectField('Student', coerce=int, validators=[DataRequired()])
    course = SelectField('Course', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Enroll Student')