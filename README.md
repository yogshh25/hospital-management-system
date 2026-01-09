# Hospital Management System

A web-based Hospital Management System designed to streamline hospital operations such as patient management, doctor records, appointments, and diagnostics.

---

## 🚀 Features

- Patient registration and management
- Doctor and staff management
- Appointment scheduling
- Diagnostic record handling
- Clean UI using HTML templates
- Modular backend structure

---

## 🛠 Tech Stack

- **Backend:** Python (Flask)
- **Frontend:** HTML, CSS (Jinja templates)
- **Database:** SQLite
- **Architecture:** MVC-style structure

---

## 📂 Project Structure

hospital-management-system/
│
├── app.py # Main Flask application
├── models.py # Database models
├── ai_service.py # Diagnostics / AI-related logic
├── fix_db.py # Database setup & fixes
├── templates/ # HTML templates
├── static/ # CSS, JS, assets
├── requirements.txt # Python dependencies
├── DIAGNOSTICS.md # Diagnostic documentation
└── .gitignore # Ignored files (venv, DB,cache)

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the repository
```bash
git clone https://github.com/yogshh25/hospital-management-system.git
cd hospital-management-system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
http://127.0.0.1:5000
To initialize or fix the database:

python fix_db.py
Future Improvements

Role-based authentication (Admin, Doctor, Patient)

Deployment on cloud (Render / Railway / AWS)

REST API separation

Improved UI/UX

Advanced diagnostics integration

Author

Yogesh Ale
B.Tech CSE Student
Focused on Backend Development, DSA, and Full Stack Projects
