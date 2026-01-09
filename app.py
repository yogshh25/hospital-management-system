from flask import Flask, render_template, request, redirect, url_for, jsonify
from models import db, Patient, Doctor, Appointment, InventoryItem
from datetime import datetime, timedelta
from ai_service import appointment_scheduler, flow_predictor, nlp_processor, inventory_alert
import json


# ---------------- HELPER FUNCTIONS ----------------
def _seed_sample_data():
    try:
        if Doctor.query.count() == 0:
            # Seed 10 sample doctors with Indian names and positions
            sample_doctors = [
                Doctor(name='Dr. Arjun Mehta', specialization='Cardiologist', position='Head of Cardiology'),
                Doctor(name='Dr. Priya Sharma', specialization='Neurologist', position='Senior Consultant, Neurology'),
                Doctor(name='Dr. Ramesh Iyer', specialization='Pediatrician', position='Consultant, Pediatrics'),
                Doctor(name='Dr. Anjali Rao', specialization='Orthopedics', position='Consultant, Orthopedics'),
                Doctor(name='Dr. Vikram Singh', specialization='General Surgery', position='Senior Surgeon'),
                Doctor(name='Dr. Sneha Patel', specialization='Gynecology', position='Consultant, Obstetrics & Gynaecology'),
                Doctor(name='Dr. Karan Gupta', specialization='Dermatology', position='Dermatologist'),
                Doctor(name='Dr. Neha Kapoor', specialization='ENT', position='ENT Specialist'),
                Doctor(name='Dr. Amit Desai', specialization='Radiology', position='Head of Radiology'),
                Doctor(name='Dr. Suman Reddy', specialization='Oncology', position='Consultant, Medical Oncology'),
            ]
            db.session.add_all(sample_doctors)
            db.session.commit()
        
        # Seed inventory items
        if InventoryItem.query.count() == 0:
            sample_inventory = [
                InventoryItem(name='Paracetamol 500mg', category='Medicine', quantity=25, unit='boxes', low_stock_threshold=10),
                InventoryItem(name='Bandages', category='Supplies', quantity=8, unit='boxes', low_stock_threshold=10),
                InventoryItem(name='Surgical Gloves', category='Equipment', quantity=15, unit='boxes', low_stock_threshold=5),
                InventoryItem(name='Antiseptic Solution', category='Medicine', quantity=12, unit='bottles', low_stock_threshold=10),
                InventoryItem(name='Syringes', category='Equipment', quantity=4, unit='boxes', low_stock_threshold=5),
            ]
            db.session.add_all(sample_inventory)
            db.session.commit()
    except Exception as e:
        print(f"Error seeding data: {e}")

def _train_ai_models():
    """Train AI models on existing data"""
    try:
        all_appts = Appointment.query.all()
        if len(all_appts) > 0:
            appts_data = []
            for appt in all_appts:
                if appt.date:
                    try:
                        patient = Patient.query.get(appt.patient_id)
                        appts_data.append({
                            'date': appt.date,
                            'doctor_id': appt.doctor_id,
                            'patient_history_count': len(patient.appointments) if patient else 0
                        })
                    except:
                        continue
            
            if appts_data:
                appointment_scheduler.train_model(appts_data)
                flow_predictor.train_model(appts_data)
    except Exception as e:
        print(f"Error training AI models: {e}")


def create_app():
    app = Flask(__name__)
    # Use an absolute path for the SQLite DB to avoid confusion about working directory / instance folder
    # This ensures the file is always created alongside this app.py, not silently in an instance folder.
    import pathlib
    base_dir = pathlib.Path(__file__).parent.resolve()
    db_path = base_dir / "meditrack.db"
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = 'dev-secret-key-change-in-production'
    print(f"[DB] Using SQLite database at: {db_path}")

    # Initialize database
    db.init_app(app)

    # Initialize database tables and data
    with app.app_context():
        try:
            db.create_all()
            print("Database initialized successfully")
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower():
                print("Database tables already exist, continuing...")
            else:
                print(f"Database initialization warning: {error_msg}")
        # --- Lightweight schema upgrade: ensure new columns exist without manual intervention ---
        try:
            from sqlalchemy import text
            with db.engine.connect() as conn:
                doctor_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(doctor);")).fetchall()]
                if 'position' not in doctor_cols:
                    conn.execute(text("ALTER TABLE doctor ADD COLUMN position VARCHAR(120);"))
                print("[DB] Added missing column doctor.position")
        except Exception as se:
            print(f"[DB] Schema check/upgrade skipped or failed: {se}")

        # --- Fill doctor positions for existing rows if empty ---
        try:
            mapping = {
                'Dr. Arjun Mehta':'Head of Cardiology',
                'Dr. Priya Sharma':'Senior Consultant, Neurology',
                'Dr. Ramesh Iyer':'Consultant, Pediatrics',
                'Dr. Anjali Rao':'Consultant, Orthopedics',
                'Dr. Vikram Singh':'Senior Surgeon',
                'Dr. Sneha Patel':'Consultant, Obstetrics & Gynaecology',
                'Dr. Karan Gupta':'Dermatologist',
                'Dr. Neha Kapoor':'ENT Specialist',
                'Dr. Amit Desai':'Head of Radiology',
                'Dr. Suman Reddy':'Consultant, Medical Oncology',
            }
            changed = False
            for d in Doctor.query.all():
                if (not getattr(d, 'position', None)) and d.name in mapping:
                    d.position = mapping[d.name]
                    changed = True
            if changed:
                db.session.commit()
                print("[DB] Backfilled doctor.position values where missing.")
        except Exception as fe:
            print(f"[DB] Position backfill skipped or failed: {fe}")
        
        _seed_sample_data()
        _train_ai_models()

    # ---------------- ROUTES ----------------
    @app.route('/')
    def index():
        patients = Patient.query.order_by(Patient.id.desc()).all()
        total_patients = len(patients)
        total_doctors = Doctor.query.count()
        return render_template('index.html',
                               patients=patients,
                               total_patients=total_patients,
                               total_doctors=total_doctors)

    @app.route('/patients/new', methods=['GET', 'POST'])
    def new_patient():
        if request.method == 'POST':
            name = request.form['name']
            dob = request.form['dob']
            contact = request.form['contact']
            new_patient = Patient(name=name, dob=dob, contact=contact)
            db.session.add(new_patient)
            db.session.commit()
            return redirect(url_for('index'))
        return render_template('patient_form.html')

    @app.route('/appointments')
    def appointments():
        doctors = Doctor.query.all()
        patients = Patient.query.all()
        return render_template('appointments.html', doctors=doctors, patients=patients)

    @app.route('/doctors')
    def doctors():
        doctors = Doctor.query.all()
        return render_template('doctors.html', doctors=doctors)

    @app.route('/reports')
    def reports():
        return render_template('report.html')

    @app.route('/inventory')
    def inventory():
        return render_template('inventory.html')

    @app.route('/test')
    def test():
        """Test route to verify server is working"""
        return render_template('test.html')

    @app.route('/ai-search')
    def ai_search():
        return render_template('ai_search.html')

    @app.route('/admin')
    def admin():
        """Admin dashboard page - redirects to index for now"""
        return redirect(url_for('index'))

    @app.route('/alerts')
    def alerts():
        """Alerts page - redirects to inventory for now"""
        return redirect(url_for('inventory'))

    @app.route('/profile', methods=['GET', 'POST'])
    def profile():
        """User profile page"""
        if request.method == 'POST':
            # Handle profile update
            name = request.form.get('name', 'Admin User')
            email = request.form.get('email', 'admin@medicare.com')
            phone = request.form.get('phone', '')
            # In a real app, save to database
            return jsonify({'success': True, 'message': 'Profile updated successfully'})
        
        # Mock user data (in a real app, fetch from database/session)
        user = {
            'name': 'Admin User',
            'email': 'admin@medicare.com',
            'phone': '+1 (555) 123-4567',
            'role': 'Administrator',
            'department': 'Hospital Management',
            'joined': 'January 2024'
        }
        return render_template('profile.html', user=user)

    @app.route('/settings', methods=['GET', 'POST'])
    def settings():
        """Settings page"""
        if request.method == 'POST':
            # Handle settings update
            data = request.get_json() if request.is_json else request.form
            setting_type = data.get('setting_type')
            # In a real app, save to database
            return jsonify({'success': True, 'message': f'{setting_type} updated successfully'})
        
        # Mock settings (in a real app, fetch from database)
        current_settings = {
            'notifications': {
                'email_notifications': True,
                'sms_notifications': False,
                'appointment_reminders': True,
                'inventory_alerts': True
            },
            'preferences': {
                'theme': 'light',
                'language': 'en',
                'timezone': 'America/New_York',
                'date_format': 'MM/DD/YYYY'
            },
            'security': {
                'two_factor': False,
                'session_timeout': 30
            }
        }
        return render_template('settings.html', settings=current_settings)

    # ---------------- API ENDPOINTS ----------------
    @app.route('/api/reports/appointments')
    def get_report_data():
        return jsonify({
            "total": 25,
            "completed": 20,
            "cancelled": 5,
            "by_doctor": {"Dr. Smith": 10, "Dr. Lee": 8, "Dr. Khan": 7},
            "by_day": {"Mon": 5, "Tue": 3, "Wed": 6, "Thu": 4, "Fri": 7}
        })

    @app.route('/api/get_slots/<int:doctor_id>/<date>')
    def get_slots(doctor_id, date):
        """Return list of available time slots"""
        def generate_slots(start_h=9, end_h=17, interval=30):
            slots = []
            cur_minutes = start_h * 60
            end_minutes = end_h * 60
            while cur_minutes < end_minutes:
                hh = cur_minutes // 60
                mm = cur_minutes % 60
                slots.append(f"{hh:02d}:{mm:02d}")
                cur_minutes += interval
            return slots

        all_slots = generate_slots()
        appts = Appointment.query.filter_by(doctor_id=doctor_id).all()
        occupied = set()
        
        for a in appts:
            if not a.date:
                continue
            try:
                dt = datetime.fromisoformat(a.date)
                adate = dt.date().isoformat()
                atime = dt.time().strftime('%H:%M')
            except Exception:
                s = a.date
                adate = s.split('T')[0] if 'T' in s else s
                atime = ''
                try:
                    atime = s.split('T')[1][:5]
                except Exception:
                    atime = ''
            if adate == date and atime:
                occupied.add(atime)

        free = [s for s in all_slots if s not in occupied]
        return jsonify(free)

    @app.route('/api/appointments/new', methods=['POST'])
    def api_new_appointment():
        data = request.get_json(force=True)
        patient_id = data.get('patient_id')
        doctor_id = data.get('doctor_id')
        appointment_date = data.get('appointment_date')
        if not (patient_id and doctor_id and appointment_date):
            return jsonify({'error': 'missing fields'}), 400
        appt = Appointment(patient_id=patient_id, doctor_id=doctor_id, date=appointment_date, status='Scheduled')
        db.session.add(appt)
        db.session.commit()
        return jsonify({'ok': True}), 201

    @app.route('/api/appointments')
    def api_list_appointments():
        appts = Appointment.query.order_by(Appointment.id.desc()).all()
        out = []
        for a in appts:
            try:
                dt = datetime.fromisoformat(a.date) if a.date else None
                adate = dt.isoformat() if dt else a.date
            except Exception:
                adate = a.date
            patient = Patient.query.get(a.patient_id)
            doctor = Doctor.query.get(a.doctor_id)
            out.append({
                'id': a.id,
                'patient': patient.name if patient else 'Unknown',
                'doctor': doctor.name if doctor else 'Unknown',
                'appointment_date': adate,
                'status': a.status
            })
        return jsonify(out)

    @app.route('/api/appointments/<int:appt_id>', methods=['DELETE'])
    def api_delete_appointment(appt_id):
        a = Appointment.query.get(appt_id)
        if not a:
            return jsonify({'error': 'not found'}), 404
        db.session.delete(a)
        db.session.commit()
        return jsonify({'ok': True}), 200

    @app.route('/api/patients/<int:patient_id>', methods=['DELETE'])
    def api_delete_patient(patient_id):
        p = Patient.query.get(patient_id)
        if not p:
            return jsonify({'error': 'not found'}), 404
        Appointment.query.filter_by(patient_id=patient_id).delete()
        db.session.delete(p)
        db.session.commit()
        return jsonify({'ok': True}), 200

    # ---------------- AI ENDPOINTS ----------------
    @app.route('/api/ai/suggest-appointment', methods=['POST'])
    def ai_suggest_appointment():
        data = request.get_json(force=True)
        doctor_id = data.get('doctor_id')
        date = data.get('date')
        
        if not doctor_id or not date:
            return jsonify({'error': 'doctor_id and date required'}), 400
        
        existing_appts = Appointment.query.filter_by(doctor_id=doctor_id).all()
        existing_appts_data = []
        for appt in existing_appts:
            try:
                if appt.date and appt.date.startswith(date):
                    existing_appts_data.append({
                        'date': appt.date,
                        'doctor_id': appt.doctor_id
                    })
            except:
                continue
        
        all_appts = Appointment.query.all()
        history_data = []
        for appt in all_appts:
            if appt.date:
                try:
                    patient = Patient.query.get(appt.patient_id)
                    history_data.append({
                        'date': appt.date,
                        'doctor_id': appt.doctor_id,
                        'patient_history_count': len(patient.appointments) if patient else 0
                    })
                except:
                    continue
        
        suggestions = appointment_scheduler.suggest_optimal_times(
            doctor_id=doctor_id,
            date=date,
            existing_appointments=existing_appts_data,
            appointments_history=history_data
        )
        
        return jsonify({
            'suggestions': suggestions,
            'doctor_id': doctor_id,
            'date': date
        })
    
    @app.route('/api/ai/predict-flow', methods=['POST'])
    def ai_predict_flow():
        data = request.get_json(force=True)
        date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        all_appts = Appointment.query.all()
        appts_data = []
        for appt in all_appts:
            try:
                if appt.date:
                    dt = datetime.fromisoformat(appt.date)
                    if dt.strftime('%Y-%m-%d') == date:
                        appts_data.append({
                            'date': appt.date,
                            'doctor_id': appt.doctor_id,
                            'patient_id': appt.patient_id,
                            'status': appt.status
                        })
            except:
                continue
        
        prediction = flow_predictor.predict_flow(date, appts_data)
        return jsonify(prediction)
    
    @app.route('/api/ai/nlp-query', methods=['POST'])
    def ai_nlp_query():
        data = request.get_json(force=True)
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'query required'}), 400
        
        parsed = nlp_processor.parse_query(query)
        result = {
            'intent': parsed['intent'],
            'entities': parsed['entities'],
            'results': []
        }
        
        if parsed['intent'] == 'today_appointments':
            date = datetime.now().strftime('%Y-%m-%d')
            appts = Appointment.query.all()
            for appt in appts:
                try:
                    if appt.date and appt.date.startswith(date):
                        patient = Patient.query.get(appt.patient_id)
                        doctor = Doctor.query.get(appt.doctor_id)
                        result['results'].append({
                            'patient': patient.name if patient else 'Unknown',
                            'doctor': doctor.name if doctor else 'Unknown',
                            'time': appt.date,
                            'status': appt.status
                        })
                except:
                    continue
        
        elif parsed['intent'] == 'doctor_appointments':
            doctor_name = parsed['entities'].get('doctor_name', '')
            date = parsed['entities'].get('date', '')
            
            doctors = Doctor.query.filter(Doctor.name.ilike(f'%{doctor_name}%')).all()
            if doctors:
                doctor_ids = [d.id for d in doctors]
                appts = Appointment.query.filter(Appointment.doctor_id.in_(doctor_ids)).all()
                
                for appt in appts:
                    try:
                        if not date or (appt.date and appt.date.startswith(date)):
                            patient = Patient.query.get(appt.patient_id)
                            doctor = Doctor.query.get(appt.doctor_id)
                            result['results'].append({
                                'patient': patient.name if patient else 'Unknown',
                                'doctor': doctor.name if doctor else 'Unknown',
                                'time': appt.date,
                                'status': appt.status
                            })
                    except:
                        continue
        
        elif parsed['intent'] == 'patient_search':
            patient_name = parsed['entities'].get('patient_name', '')
            patients = Patient.query.filter(Patient.name.ilike(f'%{patient_name}%')).all()
            for patient in patients:
                result['results'].append({
                    'id': patient.id,
                    'name': patient.name,
                    'contact': patient.contact,
                    'dob': patient.dob
                })
        
        elif parsed['intent'] == 'doctor_schedule':
            doctor_name = parsed['entities'].get('doctor_name', '')
            doctors = Doctor.query.filter(Doctor.name.ilike(f'%{doctor_name}%')).all()
            for doctor in doctors:
                appts = Appointment.query.filter_by(doctor_id=doctor.id).all()
                schedule = []
                for appt in appts:
                    if appt.date:
                        patient = Patient.query.get(appt.patient_id)
                        schedule.append({
                            'date': appt.date,
                            'patient': patient.name if patient else 'Unknown',
                            'status': appt.status
                        })
                result['results'].append({
                    'doctor': doctor.name,
                    'specialization': doctor.specialization,
                    'appointments': schedule
                })
        
        return jsonify(result)
    
    # ---------------- INVENTORY ENDPOINTS ----------------
    @app.route('/api/inventory')
    def api_list_inventory():
        items = InventoryItem.query.all()
        return jsonify([{
            'id': item.id,
            'name': item.name,
            'category': item.category,
            'quantity': item.quantity,
            'unit': item.unit,
            'low_stock_threshold': item.low_stock_threshold,
            'last_restocked': item.last_restocked
        } for item in items])
    
    @app.route('/api/inventory', methods=['POST'])
    def api_create_inventory():
        data = request.get_json(force=True)
        item = InventoryItem(
            name=data.get('name'),
            category=data.get('category', 'Supplies'),
            quantity=data.get('quantity', 0),
            unit=data.get('unit', 'units'),
            low_stock_threshold=data.get('low_stock_threshold', 10),
            last_restocked=datetime.now().isoformat()
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({'ok': True, 'id': item.id}), 201
    
    @app.route('/api/inventory/<int:item_id>', methods=['PUT'])
    def api_update_inventory(item_id):
        item = InventoryItem.query.get(item_id)
        if not item:
            return jsonify({'error': 'not found'}), 404
        
        data = request.get_json(force=True)
        if 'quantity' in data:
            item.quantity = data['quantity']
        if 'name' in data:
            item.name = data['name']
        if 'category' in data:
            item.category = data['category']
        if 'low_stock_threshold' in data:
            item.low_stock_threshold = data['low_stock_threshold']
        
        db.session.commit()
        return jsonify({'ok': True})
    
    @app.route('/api/inventory/<int:item_id>', methods=['DELETE'])
    def api_delete_inventory(item_id):
        item = InventoryItem.query.get(item_id)
        if not item:
            return jsonify({'error': 'not found'}), 404
        db.session.delete(item)
        db.session.commit()
        return jsonify({'ok': True})
    
    @app.route('/api/inventory/alerts')
    def api_inventory_alerts():
        items = InventoryItem.query.all()
        items_data = [{
            'id': item.id,
            'name': item.name,
            'quantity': item.quantity,
            'low_stock_threshold': item.low_stock_threshold
        } for item in items]
        
        alerts = inventory_alert.check_alerts(items_data)
        return jsonify({
            'alerts': alerts,
            'count': len(alerts)
        })

    return app


# ---------------- MAIN ----------------
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='127.0.0.1', port=5000)
