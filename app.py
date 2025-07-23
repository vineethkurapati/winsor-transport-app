from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, date
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'winsor_transport_secret_key'


# Database setup
def init_db():
    conn = sqlite3.connect('car_transport.db')
    c = conn.cursor()

    # Create drivers table
    c.execute('''CREATE TABLE IF NOT EXISTS drivers
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     name
                     TEXT
                     NOT
                     NULL,
                     license_number
                     TEXT
                     UNIQUE
                     NOT
                     NULL,
                     phone
                     TEXT,
                     email
                     TEXT,
                     hire_date
                     DATE,
                     status
                     TEXT
                     DEFAULT
                     'active'
                 )''')

    # Create attendance table
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
    (
        id
        INTEGER
        PRIMARY
        KEY
        AUTOINCREMENT,
        driver_id
        INTEGER,
        date
        DATE
        NOT
        NULL,
        check_in_time
        TIME,
        check_out_time
        TIME,
        status
        TEXT
        DEFAULT
        'present',
        notes
        TEXT,
        FOREIGN
        KEY
                 (
        driver_id
                 ) REFERENCES drivers
                 (
                     id
                 ))''')

    # Create fuel_bills table
    c.execute('''CREATE TABLE IF NOT EXISTS fuel_bills
    (
        id
        INTEGER
        PRIMARY
        KEY
        AUTOINCREMENT,
        driver_id
        INTEGER,
        date
        DATE
        NOT
        NULL,
        vehicle_number
        TEXT,
        fuel_type
        TEXT,
        quantity
        REAL,
        rate_per_liter
        REAL,
        total_amount
        REAL,
        bill_number
        TEXT,
        station_name
        TEXT,
        FOREIGN
        KEY
                 (
        driver_id
                 ) REFERENCES drivers
                 (
                     id
                 ))''')

    # Create daily_kilometers table
    c.execute('''CREATE TABLE IF NOT EXISTS daily_kilometers
    (
        id
        INTEGER
        PRIMARY
        KEY
        AUTOINCREMENT,
        driver_id
        INTEGER,
        date
        DATE
        NOT
        NULL,
        vehicle_number
        TEXT,
        start_km
        REAL,
        end_km
        REAL,
        total_km
        REAL,
        route
        TEXT,
        purpose
        TEXT,
        FOREIGN
        KEY
                 (
        driver_id
                 ) REFERENCES drivers
                 (
                     id
                 ))''')

    conn.commit()
    conn.close()


# Initialize database on startup
init_db()


@app.route('/')
def dashboard():
    conn = sqlite3.connect('car_transport.db')
    c = conn.cursor()

    # Get today's statistics
    today = date.today()

    # Total drivers
    c.execute("SELECT COUNT(*) FROM drivers WHERE status='active'")
    total_drivers = c.fetchone()[0]

    # Today's attendance
    c.execute("SELECT COUNT(*) FROM attendance WHERE date=?", (today,))
    present_today = c.fetchone()[0]

    # Today's fuel expenses
    c.execute("SELECT SUM(total_amount) FROM fuel_bills WHERE date=?", (today,))
    fuel_expense = c.fetchone()[0] or 0

    # Today's total kilometers
    c.execute("SELECT SUM(total_km) FROM daily_kilometers WHERE date=?", (today,))
    total_km = c.fetchone()[0] or 0

    conn.close()

    return render_template('dashboard.html',
                           total_drivers=total_drivers,
                           present_today=present_today,
                           fuel_expense=fuel_expense,
                           total_km=total_km)


@app.route('/drivers')
def drivers():
    conn = sqlite3.connect('car_transport.db')
    c = conn.cursor()
    c.execute("SELECT * FROM drivers WHERE status='active' ORDER BY name")
    drivers_list = c.fetchall()
    conn.close()
    return render_template('drivers.html', drivers=drivers_list)


@app.route('/add_driver', methods=['GET', 'POST'])
def add_driver():
    if request.method == 'POST':
        name = request.form['name']
        license_number = request.form['license_number']
        phone = request.form['phone']
        email = request.form['email']
        hire_date = request.form['hire_date']

        conn = sqlite3.connect('car_transport.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO drivers (name, license_number, phone, email, hire_date) VALUES (?, ?, ?, ?, ?)",
                      (name, license_number, phone, email, hire_date))
            conn.commit()
            flash('Driver added successfully!', 'success')
        except sqlite3.IntegrityError:
            flash('License number already exists!', 'error')
        conn.close()
        return redirect(url_for('drivers'))

    return render_template('add_driver.html')


@app.route('/attendance')
def attendance():
    conn = sqlite3.connect('car_transport.db')
    c = conn.cursor()
    today = date.today()

    # Get today's attendance with driver names
    c.execute('''SELECT a.*, d.name
                 FROM attendance a
                          JOIN drivers d ON a.driver_id = d.id
                 WHERE a.date = ?
                 ORDER BY d.name''', (today,))
    attendance_list = c.fetchall()

    # Get all active drivers
    c.execute("SELECT * FROM drivers WHERE status='active' ORDER BY name")
    drivers_list = c.fetchall()

    conn.close()
    return render_template('attendance.html', attendance=attendance_list, drivers=drivers_list)


@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    driver_id = request.form['driver_id']
    status = request.form['status']
    check_in_time = request.form.get('check_in_time')
    notes = request.form.get('notes', '')
    today = date.today()

    conn = sqlite3.connect('car_transport.db')
    c = conn.cursor()

    # Check if attendance already marked
    c.execute("SELECT id FROM attendance WHERE driver_id=? AND date=?", (driver_id, today))
    existing = c.fetchone()

    if existing:
        flash('Attendance already marked for today!', 'error')
    else:
        c.execute("INSERT INTO attendance (driver_id, date, check_in_time, status, notes) VALUES (?, ?, ?, ?, ?)",
                  (driver_id, today, check_in_time, status, notes))
        conn.commit()
        flash('Attendance marked successfully!', 'success')

    conn.close()
    return redirect(url_for('attendance'))


@app.route('/fuel_bills')
def fuel_bills():
    conn = sqlite3.connect('car_transport.db')
    c = conn.cursor()
    c.execute('''SELECT f.*, d.name
                 FROM fuel_bills f
                          JOIN drivers d ON f.driver_id = d.id
                 ORDER BY f.date DESC''')
    bills_list = c.fetchall()

    # Get all active drivers
    c.execute("SELECT * FROM drivers WHERE status='active' ORDER BY name")
    drivers_list = c.fetchall()

    conn.close()
    return render_template('fuel_bills.html', bills=bills_list, drivers=drivers_list)


@app.route('/add_fuel_bill', methods=['POST'])
def add_fuel_bill():
    driver_id = request.form['driver_id']
    date = request.form['date']
    vehicle_number = request.form['vehicle_number']
    fuel_type = request.form['fuel_type']
    quantity = float(request.form['quantity'])
    rate_per_liter = float(request.form['rate_per_liter'])
    total_amount = quantity * rate_per_liter
    bill_number = request.form['bill_number']
    station_name = request.form['station_name']

    conn = sqlite3.connect('car_transport.db')
    c = conn.cursor()
    c.execute(
        "INSERT INTO fuel_bills (driver_id, date, vehicle_number, fuel_type, quantity, rate_per_liter, total_amount, bill_number, station_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (driver_id, date, vehicle_number, fuel_type, quantity, rate_per_liter, total_amount, bill_number, station_name))
    conn.commit()
    conn.close()

    flash('Fuel bill added successfully!', 'success')
    return redirect(url_for('fuel_bills'))


@app.route('/kilometers')
def kilometers():
    conn = sqlite3.connect('car_transport.db')
    c = conn.cursor()
    c.execute('''SELECT k.*, d.name
                 FROM daily_kilometers k
                          JOIN drivers d ON k.driver_id = d.id
                 ORDER BY k.date DESC''')
    km_list = c.fetchall()

    # Get all active drivers
    c.execute("SELECT * FROM drivers WHERE status='active' ORDER BY name")
    drivers_list = c.fetchall()

    conn.close()
    return render_template('kilometers.html', kilometers=km_list, drivers=drivers_list)


@app.route('/add_kilometers', methods=['POST'])
def add_kilometers():
    driver_id = request.form['driver_id']
    date = request.form['date']
    vehicle_number = request.form['vehicle_number']
    start_km = float(request.form['start_km'])
    end_km = float(request.form['end_km'])
    total_km = end_km - start_km
    route = request.form['route']
    purpose = request.form['purpose']

    conn = sqlite3.connect('car_transport.db')
    c = conn.cursor()
    c.execute(
        "INSERT INTO daily_kilometers (driver_id, date, vehicle_number, start_km, end_km, total_km, route, purpose) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (driver_id, date, vehicle_number, start_km, end_km, total_km, route, purpose))
    conn.commit()
    conn.close()

    flash('Kilometers record added successfully!', 'success')
    return redirect(url_for('kilometers'))


if __name__ == '__main__':
    app.run(debug=True)