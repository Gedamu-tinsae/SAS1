from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField, FileField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from .models import User

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=20)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    user_type = SelectField('User Type', choices=[('', 'Select User Type'), ('student', 'Student'), ('teacher', 'Teacher'), ('admin', 'Admin')], validators=[DataRequired()])

    # Student-specific fields
    student_id = StringField('Student ID', render_kw={"placeholder": "Student ID"})
    student_name = StringField('Name', render_kw={"placeholder": "Full Name"})
    student_department = SelectField('Department', choices=[('Civil', 'Civil'), ('Structural', 'Structural'), ('Computer', 'Computer'), ('Electronics', 'Electronics'), ('Electrical', 'Electrical'), ('Mechanical', 'Mechanical'), ('IT', 'IT')])
    student_semester = SelectField('Semester', choices=[(str(i), str(i)) for i in range(1, 9)])
    student_batch = SelectField('Batch', choices=[(chr(i), chr(i)) for i in range(ord('A'), ord('G') + 1)])

    # Teacher-specific fields
    teacher_id = StringField('Teacher ID', render_kw={"placeholder": "Teacher ID"})
    teacher_name = StringField('Name', render_kw={"placeholder": "Full Name"})
    teacher_department = SelectField('Department', choices=[('Civil', 'Civil'), ('Structural', 'Structural'), ('Computer', 'Computer'), ('Electronics', 'Electronics'), ('Electrical', 'Electrical'), ('Mechanical', 'Mechanical'), ('IT', 'IT')])

    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered. Please choose a different one.')

    def validate_student_fields(self):
        if self.user_type.data == 'student':
            if not self.student_id.data:
                self.student_id.errors.append('Student ID is required for students.')
            if not self.student_name.data:
                self.student_name.errors.append('Name is required for students.')
            if self.student_id.errors or self.student_name.errors:
                return False
        return True

    def validate_teacher_fields(self):
        if self.user_type.data == 'teacher':
            if not self.teacher_id.data:
                self.teacher_id.errors.append('Teacher ID is required for teachers.')
            if not self.teacher_name.data:
                self.teacher_name.errors.append('Name is required for teachers.')
            if self.teacher_id.errors or self.teacher_name.errors:
                return False
        return True

    def validate_on_submit(self):
        # Ensure parent class validation
        if not super().validate_on_submit():
            return False

        # Custom validation
        if not self.validate_student_fields() or not self.validate_teacher_fields():
            return False

        return True


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class UploadForm(FlaskForm):
    photos = FileField('Photos', validators=[DataRequired()], render_kw={"multiple": True})
    student_id = StringField('Student ID', validators=[DataRequired()])
    submit = SubmitField('Upload')
