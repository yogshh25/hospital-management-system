"""
Script to fix database schema issues by recreating tables
Run this if you get "table already exists" errors
"""

from app import create_app
from models import db, Patient, Doctor, Appointment, InventoryItem

app = create_app()

with app.app_context():
    # Drop all tables (WARNING: This will delete all data!)
    print("Dropping all tables...")
    db.drop_all()
    
    # Create all tables fresh
    print("Creating all tables...")
    db.create_all()
    
    # Seed sample data
    print("Seeding sample data...")
    from app import _seed_sample_data
    _seed_sample_data()
    
    print("Database fixed! You can now run the server.")
    print("Note: All previous data has been deleted.")



