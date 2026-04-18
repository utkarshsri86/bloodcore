from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bloodcentre.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ── Models ──────────────────────────────────────────────────────────────────

class Donor(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    blood_group = db.Column(db.String(5),   nullable=False)
    phone       = db.Column(db.String(15))
    city        = db.Column(db.String(50))
    age         = db.Column(db.Integer)
    gender      = db.Column(db.String(10))
    last_donated= db.Column(db.String(20))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

class BloodInventory(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    blood_group = db.Column(db.String(5), nullable=False, unique=True)
    units       = db.Column(db.Integer, default=0)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BloodRequest(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    blood_group  = db.Column(db.String(5),   nullable=False)
    units_needed = db.Column(db.Integer, default=1)
    hospital     = db.Column(db.String(100))
    contact      = db.Column(db.String(15))
    status       = db.Column(db.String(20), default='Pending')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

# ── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def dashboard():
    total_donors    = Donor.query.count()
    total_requests  = BloodRequest.query.count()
    pending         = BloodRequest.query.filter_by(status='Pending').count()
    inventory       = BloodInventory.query.all()
    recent_donors   = Donor.query.order_by(Donor.created_at.desc()).limit(5).all()
    recent_requests = BloodRequest.query.order_by(BloodRequest.created_at.desc()).limit(5).all()
    return render_template('dashboard.html',
        total_donors=total_donors,
        total_requests=total_requests,
        pending=pending,
        inventory=inventory,
        recent_donors=recent_donors,
        recent_requests=recent_requests
    )

@app.route('/donors')
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
def add_donor():
    d = Donor(
        name        = request.form['name'],
        blood_group = request.form['blood_group'],
        phone       = request.form['phone'],
        city        = request.form['city'],
        age         = request.form.get('age') or None,
        gender      = request.form.get('gender'),
        last_donated= request.form.get('last_donated')
    )
    db.session.add(d)
    db.session.commit()
    return redirect('/donors')

@app.route('/delete_donor/<int:id>')
def delete_donor(id):
    Donor.query.filter_by(id=id).delete()
    db.session.commit()
    return redirect('/donors')

@app.route('/inventory')
def inventory():
    items = BloodInventory.query.all()
    return render_template('inventory.html', inventory=items)

@app.route('/update_inventory', methods=['POST'])
def update_inventory():
    bg    = request.form['blood_group']
    units = int(request.form['units'])
    item  = BloodInventory.query.filter_by(blood_group=bg).first()
    if item:
        item.units = units
    else:
        db.session.add(BloodInventory(blood_group=bg, units=units))
    db.session.commit()
    return redirect('/inventory')

@app.route('/requests')
def requests_page():
    all_req = BloodRequest.query.order_by(BloodRequest.created_at.desc()).all()
    return render_template('requests.html', requests=all_req)

@app.route('/add_request', methods=['POST'])
def add_request():
    r = BloodRequest(
        patient_name = request.form['patient_name'],
        blood_group  = request.form['blood_group'],
        units_needed = request.form.get('units_needed', 1),
        hospital     = request.form.get('hospital'),
        contact      = request.form.get('contact')
    )
    db.session.add(r)
    db.session.commit()
    return redirect('/requests')

@app.route('/update_request_status/<int:id>/<status>')
def update_request_status(id, status):
    r = BloodRequest.query.get_or_404(id)
    r.status = status
    db.session.commit()
    return redirect('/requests')

@app.route('/api/inventory')
def api_inventory():
    items = BloodInventory.query.all()
    return jsonify([{'blood_group': i.blood_group, 'units': i.units} for i in items])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Seed inventory if empty
        if BloodInventory.query.count() == 0:
            for bg in ['A+','A-','B+','B-','AB+','AB-','O+','O-']:
                db.session.add(BloodInventory(blood_group=bg, units=0))
            db.session.commit()
    app.run(debug=True)