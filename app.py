from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
import os
from dotenv import load_dotenv
load_dotenv()  # loads .env file when running locally

app = Flask(__name__)
_db_url = os.environ.get('DATABASE_URL', 'sqlite:///bloodcentre.db')
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'bloodcore2024secret-dev')
db = SQLAlchemy(app)

class Donor(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(100), nullable=False)
    blood_group  = db.Column(db.String(5), nullable=False)
    phone        = db.Column(db.String(15))
    city         = db.Column(db.String(50))
    age          = db.Column(db.Integer)
    gender       = db.Column(db.String(10))
    last_donated = db.Column(db.String(20))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

class BloodInventory(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    blood_group  = db.Column(db.String(5), nullable=False, unique=True)
    units        = db.Column(db.Integer, default=0)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BloodRequest(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    blood_group  = db.Column(db.String(5), nullable=False)
    units_needed = db.Column(db.Integer, default=1)
    hospital     = db.Column(db.String(100))
    contact      = db.Column(db.String(15))
    status       = db.Column(db.String(20), default='Pending')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

STAFF_ACCOUNTS = {
    os.environ.get('ADMIN_USER',  'admin'):  os.environ.get('ADMIN_PASS',  'bloodcore123'),
    os.environ.get('DOCTOR_USER', 'doctor'): os.environ.get('DOCTOR_PASS', 'gonda2024'),
}

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username in STAFF_ACCOUNTS and STAFF_ACCOUNTS[username] == password:
            session['logged_in'] = True
            session['username'] = username
            return redirect('/')
        else:
            error = 'Invalid username or password. Please try again.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/')
@login_required
def dashboard():
    total_donors    = Donor.query.count()
    total_requests  = BloodRequest.query.count()
    pending         = BloodRequest.query.filter_by(status='Pending').count()
    inventory       = BloodInventory.query.all()
    recent_donors   = Donor.query.order_by(Donor.created_at.desc()).limit(5).all()
    recent_requests = BloodRequest.query.order_by(BloodRequest.created_at.desc()).limit(5).all()
    return render_template('dashboard.html',
        total_donors=total_donors, total_requests=total_requests,
        pending=pending, inventory=inventory,
        recent_donors=recent_donors, recent_requests=recent_requests)

@app.route('/donors')
@login_required
def donors():
    search = request.args.get('search', '')
    bg     = request.args.get('blood_group', '')
    query  = Donor.query
    if search:
        query = query.filter(Donor.name.ilike(f'%{search}%'))
    if bg:
        query = query.filter_by(blood_group=bg)
    all_donors = query.order_by(Donor.created_at.desc()).all()
    return render_template('donors.html', donors=all_donors, search=search, bg=bg)

@app.route('/add_donor', methods=['POST'])
@login_required
def add_donor():
    d = Donor(
        name=request.form['name'], blood_group=request.form['blood_group'],
        phone=request.form.get('phone'), city=request.form.get('city'),
        age=request.form.get('age') or None, gender=request.form.get('gender'),
        last_donated=request.form.get('last_donated'))
    db.session.add(d)
    db.session.commit()
    return redirect('/donors')

@app.route('/delete_donor/<int:id>', methods=['POST'])
@login_required
def delete_donor(id):
    Donor.query.filter_by(id=id).delete()
    db.session.commit()
    return redirect('/donors')

@app.route('/inventory')
@login_required
def inventory():
    items = BloodInventory.query.all()
    return render_template('inventory.html', inventory=items)

@app.route('/update_inventory', methods=['POST'])
@login_required
def update_inventory():
    bg    = request.form['blood_group']
    units = int(request.form['units'])
    item  = BloodInventory.query.filter_by(blood_group=bg).first()
    if item:
        item.units = units
        item.updated_at = datetime.utcnow()
    else:
        db.session.add(BloodInventory(blood_group=bg, units=units))
    db.session.commit()
    return redirect('/inventory')

@app.route('/requests')
@login_required
def requests_page():
    all_req = BloodRequest.query.order_by(BloodRequest.created_at.desc()).all()
    return render_template('requests.html', requests=all_req)

@app.route('/add_request', methods=['POST'])
@login_required
def add_request():
    r = BloodRequest(
        patient_name=request.form['patient_name'], blood_group=request.form['blood_group'],
        units_needed=request.form.get('units_needed', 1),
        hospital=request.form.get('hospital'), contact=request.form.get('contact'))
    db.session.add(r)
    db.session.commit()
    return redirect('/requests')

@app.route('/update_request_status/<int:id>/<status>')
@login_required
def update_request_status(id, status):
    r = BloodRequest.query.get_or_404(id)
    r.status = status
    db.session.commit()
    return redirect('/requests')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if BloodInventory.query.count() == 0:
            for bg in ['A+','A-','B+','B-','AB+','AB-','O+','O-']:
                db.session.add(BloodInventory(blood_group=bg, units=0))
            db.session.commit()
    app.run(debug=True)