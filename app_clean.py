from flask import Flask, render_template, request, redirect, url_for, jsonify
from models import db, Patient, Doctor, Appointment, InventoryItem
from datetime import datetime, timedelta
from ai_service import appointment_scheduler, flow_predictor, nlp_processor, inventory_alert

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///meditrack.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'dev'  # Change this in production

# Initialize db
db.init_app(app)

# Create tables and seed data
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def index():
    """Dashboard page"""
    patients = Patient.query.order_by(Patient.id.desc()).all()
    total_patients = len(patients)
    total_doctors = Doctor.query.count()
    return render_template('index.html',
                         patients=patients,
                         total_patients=total_patients,
                         total_doctors=total_doctors)

@app.route('/admin')
def admin():
    """Admin dashboard page"""
    return render_template('admin.html', title='Admin Dashboard')

@app.route('/patients/new', methods=['GET', 'POST'])
def new_patient():
    """Add new patient page"""
    if request.method == 'POST':
        patient = Patient(
            name=request.form.get('name'),
            age=request.form.get('age'),
            gender=request.form.get('gender'),
            contact=request.form.get('contact'),
            medical_history=request.form.get('medical_history')
        )
        db.session.add(patient)
        db.session.commit()
        return redirect(url_for('index'))
    doctors = Doctor.query.all()
    return render_template('patient_form.html', doctors=doctors)

@app.route('/appointments')
def appointments():
    """Appointments page"""
    return render_template('appointments.html')

@app.route('/doctors')
def doctors():
    """Doctors page"""
    docs = Doctor.query.all()
    return render_template('doctors.html', doctors=docs)

@app.route('/inventory')
def inventory():
    """Inventory page"""
    return render_template('inventory.html')

@app.route('/ai-search')
def ai_search():
    """AI search page"""
    return render_template('ai_search.html')

@app.route('/reports')
def reports():
    """Reports page"""
    return render_template('reports.html')

# API Routes
@app.route('/api/admin/stats')
def admin_stats():
    """Get admin dashboard statistics"""
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    try:
        today_appointments = Appointment.query.filter(
            Appointment.date >= today,
            Appointment.date < tomorrow
        ).count()
        
        active_doctors = Doctor.query.count()
        total_patients = Patient.query.count()
        
        items = InventoryItem.query.all()
        low_stock = sum(1 for item in items if item.quantity <= item.low_stock_threshold)
        
        return jsonify({
            'todayAppointments': today_appointments,
            'activeDoctors': active_doctors,
            'lowStockItems': low_stock,
            'totalPatients': total_patients
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/settings', methods=['POST'])
def update_admin_settings():
    """Update admin settings"""
    try:
        data = request.json
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/password', methods=['POST'])
def update_admin_password():
    """Update admin password"""
    try:
        data = request.json
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/appointments')
def get_appointments():
    """Get all appointments"""
    try:
        appointments = Appointment.query.all()
        return jsonify([{
            'id': a.id,
            'patient': Patient.query.get(a.patient_id).name,
            'doctor': Doctor.query.get(a.doctor_id).name,
            'appointment_date': a.date.isoformat() if a.date else None
        } for a in appointments])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/alerts')
def inventory_alerts():
    """Get inventory alerts"""
    try:
        items = InventoryItem.query.all()
        items_data = [{
            'id': item.id,
            'name': item.name,
            'quantity': item.quantity,
            'threshold': item.low_stock_threshold
        } for item in items]

        alerts = inventory_alert.check_alerts(items_data)
        
        # Add priority levels
        for alert in alerts:
            item = next((i for i in items_data if i['name'] == alert['item']), None)
            if item:
                ratio = item['quantity'] / item['threshold']
                if ratio <= 0.3:
                    alert['level'] = 'high'
                elif ratio <= 0.6:
                    alert['level'] = 'medium'
                else:
                    alert['level'] = 'low'
        
        return jsonify({
            'alerts': alerts,
            'count': len(alerts)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)