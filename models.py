from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.String(20))
    contact = db.Column(db.String(15))
    appointments = db.relationship('Appointment', backref='patient', lazy=True)

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialization = db.Column(db.String(100))
    # position/role within the hospital (e.g. Consultant, Head of Dept)
    position = db.Column(db.String(120))
    appointments = db.relationship('Appointment', backref='doctor', lazy=True)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'))
    date = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Scheduled')

class InventoryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))  # e.g., 'Medicine', 'Equipment', 'Supplies'
    quantity = db.Column(db.Integer, default=0)
    unit = db.Column(db.String(20), default='units')  # e.g., 'boxes', 'pieces', 'ml'
    low_stock_threshold = db.Column(db.Integer, default=10)
    last_restocked = db.Column(db.String(50))
    notes = db.Column(db.Text)
