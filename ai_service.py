"""
AI Service for MediCare System
- Appointment auto-scheduling
- Patient flow prediction
- Inventory alerts
- NLP query processing
"""

try:
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    # Fallback for when scikit-learn is not available
    np = None

from datetime import datetime, timedelta
from collections import defaultdict
import re
from typing import Dict, List, Tuple, Optional
import pickle
import os


class AppointmentScheduler:
    """ML-based appointment auto-scheduling"""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def _extract_features(self, appointments_data: List[Dict], doctor_id: int, 
                         preferred_date: Optional[str] = None) -> List[List[float]]:
        """Extract features from appointment history"""
        features = []
        for appt in appointments_data:
            try:
                dt = datetime.fromisoformat(appt['date']) if isinstance(appt['date'], str) else appt['date']
                hour = dt.hour
                day_of_week = dt.weekday()
                month = dt.month
                
                # Features: hour, day_of_week, month, doctor_id, patient_history_count
                feat = [
                    hour / 24.0,  # Normalized hour
                    day_of_week / 6.0,  # Normalized day
                    month / 12.0,  # Normalized month
                    doctor_id / 100.0,  # Normalized doctor ID
                    appt.get('patient_history_count', 0) / 10.0,  # Patient appointment frequency
                ]
                features.append(feat)
            except:
                continue
        return features
    
    def train_model(self, appointments_data: List[Dict]):
        """Train the model on historical appointment data"""
        if len(appointments_data) < 10:
            # Not enough data, use simple heuristic
            self.is_trained = False
            return
        
        try:
            X = []
            y = []
            
            # Group by doctor and date to create training samples
            doctor_schedules = defaultdict(lambda: defaultdict(int))
            for appt in appointments_data:
                try:
                    dt = datetime.fromisoformat(appt['date'])
                    doctor_id = appt.get('doctor_id', 0)
                    hour = dt.hour
                    day_of_week = dt.weekday()
                    doctor_schedules[doctor_id][(day_of_week, hour)] += 1
                except:
                    continue
            
            # Create features and targets
            for appt in appointments_data:
                try:
                    dt = datetime.fromisoformat(appt['date'])
                    doctor_id = appt.get('doctor_id', 0)
                    
                    feat = [
                        dt.hour / 24.0,
                        dt.weekday() / 6.0,
                        dt.month / 12.0,
                        doctor_id / 100.0,
                        appt.get('patient_history_count', 0) / 10.0,
                    ]
                    
                    # Target: popularity score (how many appointments at this time)
                    target = doctor_schedules[doctor_id].get((dt.weekday(), dt.hour), 0)
                    
                    X.append(feat)
                    y.append(target)
                except:
                    continue
            
            if len(X) > 5 and ML_AVAILABLE:
                X = np.array(X)
                y = np.array(y)
                
                self.scaler.fit(X)
                X_scaled = self.scaler.transform(X)
                
                self.model = RandomForestRegressor(n_estimators=50, random_state=42, max_depth=5)
                self.model.fit(X_scaled, y)
                self.is_trained = True
            elif len(X) > 5:
                # ML not available, use heuristic mode
                self.is_trained = False
        except Exception as e:
            print(f"Training error: {e}")
            self.is_trained = False
    
    def suggest_optimal_times(self, doctor_id: int, date: str, 
                             existing_appointments: List[Dict],
                             appointments_history: List[Dict] = None) -> List[Dict]:
        """Suggest optimal appointment times using ML"""
        try:
            target_date = datetime.fromisoformat(date) if isinstance(date, str) else date
            if isinstance(target_date, str):
                target_date = datetime.strptime(date, '%Y-%m-%d')
            
            # Generate candidate time slots
            slots = []
            for hour in range(9, 17):  # 9 AM to 5 PM
                for minute in [0, 30]:
                    slot_time = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    slots.append(slot_time)
            
            # Filter out occupied slots
            occupied_times = set()
            for appt in existing_appointments:
                try:
                    appt_time = datetime.fromisoformat(appt['date'])
                    occupied_times.add((appt_time.hour, appt_time.minute))
                except:
                    continue
            
            # Score available slots
            scored_slots = []
            for slot in slots:
                if (slot.hour, slot.minute) in occupied_times:
                    continue
                
                if self.is_trained and appointments_history and ML_AVAILABLE:
                    # Use ML model to score
                    feat = np.array([[
                        slot.hour / 24.0,
                        slot.weekday() / 6.0,
                        slot.month / 12.0,
                        doctor_id / 100.0,
                        0.0  # New patient
                    ]])
                    feat_scaled = self.scaler.transform(feat)
                    score = self.model.predict(feat_scaled)[0]
                else:
                    # Use heuristic: prefer mid-morning and early afternoon
                    if 10 <= slot.hour <= 14:
                        score = 0.8
                    elif 9 <= slot.hour <= 15:
                        score = 0.6
                    else:
                        score = 0.4
                
                scored_slots.append({
                    'time': slot.isoformat(),
                    'time_display': slot.strftime('%H:%M'),
                    'score': float(score),
                    'reason': 'ML recommended' if self.is_trained else 'Heuristic'
                })
            
            # Sort by score (highest first)
            scored_slots.sort(key=lambda x: x['score'], reverse=True)
            return scored_slots[:5]  # Return top 5 suggestions
            
        except Exception as e:
            print(f"Error in suggest_optimal_times: {e}")
            return []


class PatientFlowPredictor:
    """Predict patient flow and no-shows"""
    
    def __init__(self):
        self.model = None
        self.is_trained = False
    
    def train_model(self, appointments_data: List[Dict]):
        """Train model on historical data"""
        if len(appointments_data) < 10:
            self.is_trained = False
            return
        
        try:
            # Simple heuristic-based model for now
            # In production, would use more sophisticated ML
            self.is_trained = True
        except:
            self.is_trained = False
    
    def predict_flow(self, date: str, appointments: List[Dict]) -> Dict:
        """Predict patient flow for a given date"""
        try:
            target_date = datetime.fromisoformat(date) if isinstance(date, str) else date
            if isinstance(target_date, str):
                target_date = datetime.strptime(date, '%Y-%m-%d')
            
            # Count appointments by hour
            hourly_counts = defaultdict(int)
            for appt in appointments:
                try:
                    appt_time = datetime.fromisoformat(appt['date'])
                    if appt_time.date() == target_date.date():
                        hourly_counts[appt_time.hour] += 1
                except:
                    continue
            
            # Predict busy times
            predicted_peak_hours = []
            for hour in range(9, 17):
                count = hourly_counts.get(hour, 0)
                if count >= 3:
                    predicted_peak_hours.append({
                        'hour': hour,
                        'predicted_count': count,
                        'status': 'busy' if count >= 5 else 'moderate'
                    })
            
            # Predict no-shows (simple heuristic: 10% no-show rate)
            total_appointments = len([a for a in appointments 
                                    if datetime.fromisoformat(a['date']).date() == target_date.date()])
            predicted_no_shows = int(total_appointments * 0.1)
            
            return {
                'date': date,
                'total_appointments': total_appointments,
                'predicted_peak_hours': predicted_peak_hours,
                'predicted_no_shows': predicted_no_shows,
                'expected_arrivals': total_appointments - predicted_no_shows,
                'busy_periods': [h for h in predicted_peak_hours if h['status'] == 'busy']
            }
        except Exception as e:
            print(f"Error in predict_flow: {e}")
            return {'error': str(e)}


class NLPQueryProcessor:
    """NLP processor for natural language queries"""
    
    def __init__(self):
        # Patterns for common queries
        self.patterns = {
            'today_appointments': [
                r"show.*today.*appointments",
                r"today.*appointments",
                r"appointments.*today",
                r"what.*appointments.*today"
            ],
            'doctor_appointments': [
                r"show.*appointments.*(?:for|with).*dr\.?\s*(\w+)",
                r"appointments.*dr\.?\s*(\w+)",
                r"dr\.?\s*(\w+).*appointments"
            ],
            'patient_search': [
                r"find.*patient.*(\w+)",
                r"search.*patient.*(\w+)",
                r"patient.*named.*(\w+)"
            ],
            'schedule_appointment': [
                r"schedule.*appointment",
                r"book.*appointment",
                r"create.*appointment"
            ],
            'doctor_schedule': [
                r"show.*schedule.*(?:for|of).*dr\.?\s*(\w+)",
                r"when.*dr\.?\s*(\w+).*available"
            ]
        }
    
    def parse_query(self, query: str) -> Dict:
        """Parse natural language query"""
        query_lower = query.lower().strip()
        
        result = {
            'intent': 'unknown',
            'entities': {},
            'original_query': query
        }
        
        # Check for today's appointments
        for pattern in self.patterns['today_appointments']:
            if re.search(pattern, query_lower):
                result['intent'] = 'today_appointments'
                result['entities']['date'] = datetime.now().strftime('%Y-%m-%d')
                return result
        
        # Check for doctor-specific appointments
        for pattern in self.patterns['doctor_appointments']:
            match = re.search(pattern, query_lower)
            if match:
                result['intent'] = 'doctor_appointments'
                result['entities']['doctor_name'] = match.group(1).title()
                # Check for date keywords
                if 'today' in query_lower:
                    result['entities']['date'] = datetime.now().strftime('%Y-%m-%d')
                elif 'tomorrow' in query_lower:
                    result['entities']['date'] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                return result
        
        # Check for patient search
        for pattern in self.patterns['patient_search']:
            match = re.search(pattern, query_lower)
            if match:
                result['intent'] = 'patient_search'
                result['entities']['patient_name'] = match.group(1).title()
                return result
        
        # Check for schedule appointment
        for pattern in self.patterns['schedule_appointment']:
            if re.search(pattern, query_lower):
                result['intent'] = 'schedule_appointment'
                return result
        
        # Check for doctor schedule
        for pattern in self.patterns['doctor_schedule']:
            match = re.search(pattern, query_lower)
            if match:
                result['intent'] = 'doctor_schedule'
                result['entities']['doctor_name'] = match.group(1).title()
                return result
        
        return result


class InventoryAlertSystem:
    """Inventory management and alerts"""
    
    def __init__(self):
        self.low_stock_threshold = 10
        self.critical_threshold = 5
    
    def check_alerts(self, inventory_items: List[Dict]) -> List[Dict]:
        """Check for inventory alerts"""
        alerts = []
        
        for item in inventory_items:
            stock_level = item.get('quantity', 0)
            item_name = item.get('name', 'Unknown')
            
            if stock_level <= self.critical_threshold:
                alerts.append({
                    'type': 'critical',
                    'item': item_name,
                    'quantity': stock_level,
                    'message': f'CRITICAL: {item_name} is running very low ({stock_level} remaining)',
                    'priority': 'high'
                })
            elif stock_level <= self.low_stock_threshold:
                alerts.append({
                    'type': 'warning',
                    'item': item_name,
                    'quantity': stock_level,
                    'message': f'WARNING: {item_name} is running low ({stock_level} remaining)',
                    'priority': 'medium'
                })
        
        return alerts
    
    def predict_restock_date(self, item: Dict, daily_usage: float = 1.0) -> Optional[str]:
        """Predict when inventory will need restocking"""
        current_stock = item.get('quantity', 0)
        if daily_usage <= 0:
            return None
        
        days_remaining = current_stock / daily_usage
        restock_date = datetime.now() + timedelta(days=int(days_remaining))
        return restock_date.strftime('%Y-%m-%d')


# Global instances
appointment_scheduler = AppointmentScheduler()
flow_predictor = PatientFlowPredictor()
nlp_processor = NLPQueryProcessor()
inventory_alert = InventoryAlertSystem()

