from flask import Flask, render_template, request, redirect, url_for, jsonify
from models import db, Patient, Doctor, Appointment, InventoryItem
from datetime import datetime, timedelta
from ai_service import appointment_scheduler, flow_predictor, nlp_processor, inventory_alert
import json

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///meditrack.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = 'dev'  # Change this to a proper secret key in production

    # Initialize db with app
    db.init_app(app)

    # Routes
    @app.route('/')
    def index():
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
            # In a real app, you would update the admin user in the database
            return jsonify({'status': 'success'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/admin/password', methods=['POST'])
    def update_admin_password():
        """Update admin password"""
        try:
            data = request.json
            # In a real app, you would verify the current password and update with the new one
            return jsonify({'status': 'success'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)