from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from .forms import RegistrationForm, LoginForm, UploadForm
from .models import User, AttendanceRecord, ScheduleEntry,Student, Teacher, Class, AttendanceStatus
from . import db
from datetime import datetime
import os
import cv2
import numpy as np
import base64
from werkzeug.utils import secure_filename
from app import db
from .utils import calculate_attendance_percentage, get_attendance_details
from app.facial_recognition import train_model as train_model_function, recognize_face
from app.facial_recognition import train_model
import io
from PIL import Image
from flask import abort


# Define the main blueprint
main = Blueprint('main', __name__)

@main.route('/')
def index():
    return redirect(url_for('main.login'))

@main.route('/student_options')
@login_required
def student_options():
    # Query student based on the current user
    student = Student.query.filter_by(user_id=current_user.id).first()

    if student:
        # Fetch attendance records for the student
        attendance_records = AttendanceRecord.query.filter_by(student_id=student.id).all()

        # Fetch schedule entries for the student
        schedule_entries = ScheduleEntry.query.filter_by(student_id=student.id).all()

        # Check if attendance is enabled for any of the student's scheduled classes
        can_take_attendance = any(
            AttendanceStatus.query.filter_by(day=entry.day_of_week, period=f"{entry.time_start}-{entry.time_end}").first() is not None and
            AttendanceStatus.query.filter_by(day=entry.day_of_week, period=f"{entry.time_start}-{entry.time_end}").first().status
            for entry in schedule_entries
        )
    else:
        attendance_records = []
        can_take_attendance = False

    return render_template('student_options.html', attendance_records=attendance_records, can_take_attendance=can_take_attendance)



@main.route('/take_attendance', methods=['GET', 'POST'])
@login_required
def take_attendance():
    day = request.args.get('day')
    period = request.args.get('period')

    # Fetch attendance status for the specified day and period
    attendance_status = AttendanceStatus.query.filter_by(day=day, period=period).first()

    if request.method == 'POST':
        if not attendance_status or not attendance_status.status:
            flash('Attendance is not available for this class at this time.', 'warning')
            return redirect(url_for('main.student_options'))

        # Process the attendance capture
        # Example: record the attendance
        class_id = Class.query.filter_by(schedule=day).first().id  # Adjust as needed
        new_record = AttendanceRecord(
            student_id=current_user.id,
            class_id=class_id,
            timestamp=datetime.utcnow(),
            present=True
        )
        db.session.add(new_record)
        db.session.commit()

        flash('Attendance recorded successfully!', 'success')
        return redirect(url_for('main.student_options'))

    flash(f'Taking attendance for {day} during {period}.', 'info')
    return render_template('take_attendance.html', day=day, period=period)




@main.route('/process_attendance', methods=['POST'])
@login_required
def process_attendance():
    try:
        if 'image_data' in request.json:
            image_data = request.json['image_data']
            student_id = recognize_face(image_data, None)  # Adjust if you have a specific student ID
            if student_id is not None:
                attendance_record = AttendanceRecord(student_id=student_id, timestamp=datetime.now())
                db.session.add(attendance_record)
                db.session.commit()
                student = User.query.filter_by(id=student_id).first()
                student_name = student.username
                return jsonify({'success': True, 'student_name': student_name}), 200
            else:
                return jsonify({'success': False, 'error': 'Face not recognized.'}), 400
        else:
            return jsonify({'success': False, 'error': 'No image data received.'}), 400
    except Exception as e:
        logging.error(f"Error processing attendance: {e}")
        return jsonify({'success': False, 'error': 'An error occurred while processing attendance.'}), 500




@main.route('/attendance')
@login_required
def attendance():
    student = Student.query.filter_by(user_id=current_user.id).first()
    if student:
        attendance_records = AttendanceRecord.query.filter_by(student_id=student.id).all()
    else:
        attendance_records = []
    if not attendance_records:
        flash('No attendance records found. Please take attendance first.', 'info')
        return redirect(url_for('main.student_options'))

    course_attendance = {}
    for record in attendance_records:
        course_name = record.course.name  # Assuming course refers to the related class
        if course_name not in course_attendance:
            course_attendance[course_name] = {
                'total_classes': 0,
                'attended_classes': 0
            }
        course_attendance[course_name]['total_classes'] += 1
        if record.attended:
            course_attendance[course_name]['attended_classes'] += 1

    for course, data in course_attendance.items():
        total_classes = data['total_classes']
        attended_classes = data['attended_classes']
        if total_classes > 0:
            data['attendance_percentage'] = int((attended_classes / total_classes) * 100)
        else:
            data['attendance_percentage'] = 0

    return render_template('attendance.html', attendance_records=attendance_records, course_attendance=course_attendance)

@main.route('/admin_dashboard')
def admin_dashboard():
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for('main.login'))  # Redirect to login if not authenticated or not an admin

    return render_template('admin_dashboard.html')

@main.route('/teacher-options', methods=['GET', 'POST'])
@login_required
def teacher_options():
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    periods = ['08:00-09:00', '09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-01:00']
    
    schedule = {day: {period: None for period in periods} for day in days}

    if current_user.is_teacher:
        # Teacher's schedule created by admin
        schedule_entries = ScheduleEntry.query.filter_by(teacher_id=current_user.id).all()
        for entry in schedule_entries:
            period_key = f"{entry.time_start}-{entry.time_end}"
            schedule[entry.day_of_week][period_key] = entry.classroom
    else:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))

    # No POST handling needed for schedule creation/update by teachers

    return render_template('teacher_options.html', days=days, periods=periods, schedule=schedule)


@main.route('/toggle_attendance', methods=['POST'])
@login_required
def toggle_attendance():
    day = request.form['day']
    period = request.form['period']
    status = request.form['status']
    
    # Logic to toggle attendance status
    # Example of saving the status to the database
    attendance = AttendanceStatus.query.filter_by(day=day, period=period).first()
    if not attendance:
        attendance = AttendanceStatus(day=day, period=period, status=(status == 'ON'))
        db.session.add(attendance)
    else:
        attendance.status = (status == 'ON')
    
    db.session.commit()

    flash('Attendance status updated successfully!', 'success')
    return redirect(url_for('main.attendance_control'))


@main.route('/attendance_records', methods=['GET'])
@login_required
def attendance_records():
    students = Student.query.all()
    # Calculate attendance percentage for each student
    # You should have a method to compute this
    student_data = [{'id': student.id, 'attendance_percentage': calculate_attendance_percentage(student)} for student in students]
    return render_template('attendance_records.html', students=student_data)

@main.route('/student_attendance/<int:student_id>', methods=['GET'])
@login_required
def student_attendance(student_id):
    # Fetch attendance details for the student
    student = Student.query.get_or_404(student_id)
    # Assuming you have a method to get detailed attendance records
    records = get_attendance_details(student)
    return render_template('student_attendance.html', student=student, records=records)


from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required

@main.route('/attendance_control', methods=['GET', 'POST'])
@login_required
def attendance_control():
    if not current_user.is_teacher:
        abort(403)  # Forbidden if the user is not a teacher

    if request.method == 'POST':
        # Extract form data
        day = request.form.get('day')
        period = request.form.get('period')
        status = request.form.get('status') == 'ON'

        # Update or create attendance status
        attendance_status = AttendanceStatus.query.filter_by(day=day, period=period).first()
        if not attendance_status:
            attendance_status = AttendanceStatus(day=day, period=period, status=status)
            db.session.add(attendance_status)
        else:
            attendance_status.status = status
        db.session.commit()

        flash('Attendance control updated!', 'success')
        return redirect(url_for('main.attendance_control'))

    # Default state or fetch state from database
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    periods = ['10:30-11:30', '11:30-12:30', '12:30-1:30', '1:30-2:00', '2:00-3:00', '3:00-4:00', '4:00-5:00', '5:00-6:00']
    attendance = {day: {period: False for period in periods} for day in days}

    # Fetch current attendance status from the database
    for day in days:
        for period in periods:
            status = AttendanceStatus.query.filter_by(day=day, period=period).first()
            if status:
                attendance[day][period] = status.status

    return render_template('attendance_control.html', days=days, periods=periods, attendance=attendance)



@main.route('/attendance_records', endpoint='attendance_records_main')
@login_required
def attendance_records():
    attendance_records = AttendanceRecord.query.all()
    return render_template('attendance_records.html', attendance_records=attendance_records)


import traceback

@main.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(
            email=form.email.data,
            password=hashed_password,
            is_teacher=form.user_type.data == 'teacher',
            is_admin=form.user_type.data == 'admin'
        )
        db.session.add(user)
        db.session.commit()

        if form.user_type.data == 'student':
            student = Student(
                user_id=user.id,
                student_id=form.student_id.data,
                name=form.student_name.data,
                department=form.student_department.data,
                semester=form.student_semester.data,
                batch=form.student_batch.data
            )
            db.session.add(student)

        elif form.user_type.data == 'teacher':
            teacher = Teacher(
                user_id=user.id,
                teacher_id=form.teacher_id.data,
                name=form.teacher_name.data,
                department=form.teacher_department.data
            )
            db.session.add(teacher)

        db.session.commit()
        flash('Account created successfully!', 'success')
        return redirect(url_for('main.login'))

    return render_template('register.html', form=form)

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_teacher:
            return redirect(url_for('main.teacher_options'))  # Redirect to schedule.html for teachers
        elif current_user.is_admin:
            return redirect(url_for('main.admin_dashboard'))  # Redirect to admin_dashboard.html for admins
        else:
            return redirect(url_for('main.student_options'))  # Redirect to student_options.html for students

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            current_app.logger.info(f"User {user.email} logged in successfully. Is teacher: {user.is_teacher}, Is admin: {user.is_admin}")

            if user.is_teacher:
                return redirect(url_for('main.teacher_options'))  # Redirect to schedule.html for teachers
            elif user.is_admin:
                return redirect(url_for('main.admin_dashboard'))  # Redirect to admin_dashboard.html for admins
            else:
                return redirect(url_for('main.student_options'))  # Redirect to student_options.html for students
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
            current_app.logger.warning('Login failed. Invalid email or password.')

    current_app.logger.debug(f"Form errors: {form.errors}")
    return render_template('login.html', form=form)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/train_model', methods=['GET', 'POST'])
@login_required
def train_model_route():
    form = UploadForm()
    training_complete = False

    if form.validate_on_submit():
        uploaded_files = request.files.getlist('photos')  # List of FileStorage objects
        student_id = form.student_id.data

        if not student_id:
            flash('Student ID is required.', 'danger')
            return redirect(url_for('main.train_model_route'))

        images = []
        for file in uploaded_files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                
                try:
                    file.save(file_path)
                    image = cv2.imread(file_path)
                    
                    if image is not None:
                        # Print the shape of the image to ensure it's loaded correctly
                        print(f"Image shape: {image.shape}")
                        images.append(image)
                    else:
                        flash(f'Error reading image file: {filename}', 'warning')

                except Exception as e:
                    flash(f'Error processing file {filename}: {str(e)}', 'danger')
                    continue

        if images:
            flash('Photos uploaded. Training in progress...', 'info')
            db.session.commit()  # Ensure any previous changes are committed

            # Train the model using the CNN approach
            try:
                success = train_model(student_id, images)  # Ensure train_model is correctly imported and defined
                if success:
                    flash('Model trained successfully!', 'success')
                    training_complete = True
                    return redirect(url_for('main.test_model'))
                else:
                    flash('Failed to train model. Please try again.', 'danger')
            except Exception as e:
                flash(f'Error during model training: {str(e)}', 'danger')
        else:
            flash('No valid images uploaded.', 'danger')

    return render_template('train_model.html', form=form, training_complete=training_complete)


@main.route('/test_model')
@login_required
def test_model():
    return render_template('test_model.html')

@main.route('/recognize_face', methods=['POST'])
def recognize_face_route():
    data = request.get_json()
    image_data = data.get('image')
    student_id = data.get('student_id')

    if not image_data or not student_id:
        return jsonify({'error': 'Invalid request'}), 400

    try:
        # Recognize face
        recognized_id = recognize_face(image_data, student_id)
        if recognized_id:
            return jsonify({'student_id': recognized_id})
        else:
            return jsonify({'error': 'No student recognized'})
    except Exception as e:
        logging.error(f"Error during face recognition: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred. Check the log for details.'}), 500


@main.route('/create_schedule_student', methods=['GET', 'POST'])
@login_required
def create_schedule_student():
    if not current_user.is_admin:
        abort(403)

    departments = Student.query.with_entities(Student.department).distinct().all()
    semesters = [str(i) for i in range(1, 9)]
    batches = [chr(i) for i in range(ord('A'), ord('G') + 1)]
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    periods = ['10:30-11:30', '11:30-12:30', '12:30-1:30', '1:30-2:00', '2:00-3:00', '3:00-4:00', '4:00-5:00', '5:00-6:00']
    teachers = Teacher.query.all()

    if request.method == 'POST':
        department = request.form['department']
        semester = request.form['semester']
        batch = request.form['batch']
        day_of_week = request.form['day_of_week']
        time_start = request.form['time_start']
        time_end = request.form['time_end']
        classroom = request.form['classroom']
        teacher_id = request.form['teacher_id']  # New field

        students = Student.query.filter_by(department=department, semester=semester, batch=batch).all()
        for student in students:
            existing_entry = ScheduleEntry.query.filter_by(
                student_id=student.id,
                day_of_week=day_of_week,
                time_start=time_start,
                time_end=time_end
            ).first()
            if existing_entry:
                existing_entry.classroom = classroom
                existing_entry.teacher_id = teacher_id
            else:
                new_entry = ScheduleEntry(
                    student_id=student.id,
                    day_of_week=day_of_week,
                    time_start=time_start,
                    time_end=time_end,
                    classroom=classroom,
                    teacher_id=teacher_id
                )
                db.session.add(new_entry)
        db.session.commit()
        flash('Student schedule updated successfully!', 'success')
        return redirect(url_for('main.create_schedule_student'))

    return render_template('create_schedule_student.html', departments=departments, semesters=semesters, batches=batches, days=days, periods=periods, teachers=teachers)



@main.route('/create_schedule_teacher', methods=['GET', 'POST'])
@login_required
def create_schedule_teacher():
    if not current_user.is_admin:
        abort(403)

    teachers = Teacher.query.all()
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    periods = ['10:30-11:30', '11:30-12:30', '12:30-1:30', '1:30-2:00', '2:00-3:00', '3:00-4:00', '4:00-5:00', '5:00-6:00']
    
    if request.method == 'POST':
        teacher_id = request.form['teacher_id']
        day_of_week = request.form['day_of_week']
        time_start = request.form['time_start']
        time_end = request.form['time_end']
        classroom = request.form['classroom']

        existing_entry = ScheduleEntry.query.filter_by(
            teacher_id=teacher_id,
            day_of_week=day_of_week,
            time_start=time_start,
            time_end=time_end
        ).first()

        if existing_entry:
            existing_entry.classroom = classroom
        else:
            new_entry = ScheduleEntry(
                teacher_id=teacher_id,
                day_of_week=day_of_week,
                time_start=time_start,
                time_end=time_end,
                classroom=classroom
            )
            db.session.add(new_entry)
        db.session.commit()
        flash('Teacher schedule updated successfully!', 'success')
        return redirect(url_for('main.create_schedule_teacher'))

    # Handle GET request to display existing schedules
    teacher_id = request.args.get('teacher_id')
    existing_schedules = []

    if teacher_id:
        existing_schedules = ScheduleEntry.query.filter_by(teacher_id=teacher_id).all()

    return render_template('create_schedule_teacher.html', teachers=teachers, days=days, periods=periods, existing_schedules=existing_schedules)



@main.route('/view_schedule')
@login_required
def view_schedule():
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        abort(404)

    schedule_entries = ScheduleEntry.query.filter(
        ScheduleEntry.student_id == student.id
    ).all()

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    periods = ['10:30-11:30', '11:30-12:30', '12:30-1:30', '1:30-2:00', '2:00-3:00', '3:00-4:00', '4:00-5:00', '5:00-6:00']

    # Initialize the schedule dictionary
    schedule = {day: {period: None for period in periods} for day in days}

    for entry in schedule_entries:
        period_key = f"{entry.time_start}-{entry.time_end}"
        schedule[entry.day_of_week][period_key] = entry.classroom

    return render_template('view_schedule.html', days=days, periods=periods, schedule=schedule)

@main.route('/view_schedule_teacher')
@login_required
def view_schedule_teacher():
    if not current_user.is_teacher:
        abort(403)  # Forbidden if the user is not a teacher

    # Query schedule entries for the teacher
    schedule_entries = ScheduleEntry.query.filter_by(teacher_id=current_user.teacher_profile.id).all()

    # Query attendance status for the teacher's schedule
    attendance_entries = AttendanceStatus.query.all()
    attendance_status = {(entry.day, entry.period): entry.status for entry in attendance_entries}

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    periods = ['10:30-11:30', '11:30-12:30', '12:30-1:30', '1:30-2:00', '2:00-3:00', '3:00-4:00', '4:00-5:00', '5:00-6:00']

    # Initialize the schedule dictionary
    schedule = {day: {period: None for period in periods} for day in days}

    for entry in schedule_entries:
        period_key = f"{entry.time_start}-{entry.time_end}"
        if period_key in schedule[entry.day_of_week]:
            schedule[entry.day_of_week][period_key] = entry.classroom

    return render_template(
        'view_schedule_teacher.html', 
        days=days, 
        periods=periods, 
        schedule=schedule,
        attendance_status=attendance_status
    )


import logging
from flask import request, render_template, abort
from sqlalchemy import and_
from sqlalchemy.orm import aliased

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@main.route('/admin_view_schedules', methods=['GET', 'POST'])
@login_required
def admin_view_schedules():
    if not current_user.is_admin:
        abort(403)  # Forbidden if the user is not an admin

    # Retrieve distinct filter options
    departments = [dept[0] for dept in db.session.query(Teacher.department).distinct()]
    semesters = [sem[0] for sem in db.session.query(Student.semester).distinct()]
    batches = [batch[0] for batch in db.session.query(Student.batch).distinct()]
    teachers = [teacher.id for teacher in Teacher.query.all()]

    # Get filter values from request arguments
    filters = {
        'department': request.args.get('department'),
        'semester': request.args.get('semester'),
        'batch': request.args.get('batch'),
        'teacher_id': request.args.get('teacher_id')
    }

    # Log filter values
    logger.info(f"Filters applied: {filters}")

    # Build query based on filters
    schedule_entries = ScheduleEntry.query

    # Create table aliases
    StudentAlias = aliased(Student)

    if filters['department']:
        schedule_entries = schedule_entries.join(Teacher).filter(Teacher.department == filters['department'])
    if filters['semester'] or filters['batch']:
        schedule_entries = schedule_entries.join(StudentAlias).filter(
            and_(
                (StudentAlias.semester == filters['semester']) if filters['semester'] else True,
                (StudentAlias.batch == filters['batch']) if filters['batch'] else True
            )
        )
    if filters['teacher_id']:
        schedule_entries = schedule_entries.filter(ScheduleEntry.teacher_id == filters['teacher_id'])

    # Log the generated SQL query
    query_str = str(schedule_entries.statement.compile(compile_kwargs={"literal_binds": True}))
    logger.info(f"Generated SQL query: {query_str}")

    schedule_entries = schedule_entries.all()

    # Initialize the schedule dictionary
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    periods = ['10:30-11:30', '11:30-12:30', '12:30-1:30', '1:30-2:00', '2:00-3:00', '3:00-4:00', '4:00-5:00', '5:00-6:00']
    schedule = {day: {period: [] for period in periods} for day in days}

    for entry in schedule_entries:
        period_key = f"{entry.time_start}-{entry.time_end}"
        if period_key in schedule[entry.day_of_week]:
            schedule[entry.day_of_week][period_key].append({
                'classroom': entry.classroom,
                'teacher_id': entry.teacher_id
            })

    return render_template('admin_view_schedules.html', days=days, periods=periods, schedule=schedule,
                           departments=departments, semesters=semesters, batches=batches, teachers=teachers,
                           filters=filters)

