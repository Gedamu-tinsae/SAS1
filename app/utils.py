from datetime import datetime
from app.models import AttendanceRecord, Student, Class  # Import necessary models
from app import db


def is_on_campus(latitude, longitude):
    # Check if the given coordinates are within the campus boundaries
    ...

def calculate_attendance_percentage(student):
    # Calculate the attendance percentage for a given student
    total_classes = db.session.query(AttendanceRecord).filter_by(student_id=student.id).count()
    attended_classes = db.session.query(AttendanceRecord).filter_by(student_id=student.id, present=True).count()
    if total_classes == 0:
        return 0
    return (attended_classes / total_classes) * 100

def get_attendance_details(student):
    # Fetch detailed attendance records for the given student
    records = db.session.query(AttendanceRecord).filter_by(student_id=student.id).all()
    return records
