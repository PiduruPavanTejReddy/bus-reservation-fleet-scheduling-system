"""
BUS RESERVATION AND FLEET SCHEDULING SYSTEM
Full-Stack Flask Application
Target DBMS: MySQL 8.0+
"""

import os
import uuid
from datetime import datetime, timedelta
from functools import wraps
import mysql.connector
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, jsonify, g
)
from werkzeug.security import check_password_hash, generate_password_hash
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# -----------------------------------------------------------------------------
# DATABASE CONNECTION HELPER
# -----------------------------------------------------------------------------
def get_db():
    """Get a thread-safe connection to MySQL database."""
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            port=app.config['MYSQL_PORT'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB'],
            autocommit=False
        )
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None and db.is_connected():
        db.close()

def query_db(query, args=(), one=False, commit=False):
    """Execute a query and fetch results as a dictionary list."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, args)
        if commit:
            conn.commit()
            return cursor.lastrowid
        rv = cursor.fetchall()
        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        if commit:
            conn.rollback()
        raise e
    finally:
        cursor.close()

# -----------------------------------------------------------------------------
# AUTHENTICATION DECORATOR
# -----------------------------------------------------------------------------
def login_required(f):
    """Protect routes requiring administrative authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# -----------------------------------------------------------------------------
# AUTHENTICATION ROUTES
# -----------------------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin and operator authentication."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = query_db(
            "SELECT user_id, username, password_hash, full_name, role FROM admin_users WHERE username = %s",
            (username,), one=True
        )

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            flash(f"Welcome back, {user['full_name']} ({user['role']})!", 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Terminate the authenticated session."""
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

# -----------------------------------------------------------------------------
# DASHBOARD
# -----------------------------------------------------------------------------
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    """Main administrative dashboard with live aggregated database metrics."""
    # Aggregated key metrics
    total_buses = query_db("SELECT COUNT(*) AS cnt FROM buses", one=True)['cnt']
    active_trips = query_db(
        "SELECT COUNT(*) AS cnt FROM trips WHERE trip_status IN ('PUBLISHED', 'SCHEDULED')",
        one=True
    )['cnt']
    total_passengers = query_db("SELECT COUNT(*) AS cnt FROM passengers", one=True)['cnt']
    total_bookings = query_db(
        "SELECT COUNT(*) AS cnt FROM bookings WHERE booking_status = 'CONFIRMED'",
        one=True
    )['cnt']
    
    # Financial metrics using aggregation & joins
    revenue_data = query_db("""
        SELECT 
            COALESCE(SUM(CASE WHEN bk.booking_status = 'CONFIRMED' THEN bk.total_amount ELSE 0 END), 0) AS gross,
            COALESCE(SUM(c.refund_amount), 0) AS refunds
        FROM bookings bk
        LEFT JOIN cancellations c ON bk.booking_id = c.booking_id
    """, one=True)
    net_revenue = revenue_data['gross'] - revenue_data['refunds']

    # Fleet utilization from analytical view
    utilization_stat = query_db(
        "SELECT ROUND(AVG(occupancy_percentage), 1) AS avg_occ FROM trip_occupancy_view",
        one=True
    )['avg_occ'] or 0.0

    # Upcoming trips
    upcoming_trips = query_db("""
        SELECT 
            t.trip_id, r.route_name, b.bus_number, b.bus_type,
            t.departure_time, t.trip_status, f.amount AS fare
        FROM trips t
        JOIN routes r ON t.route_id = r.route_id
        JOIN buses b ON t.bus_id = b.bus_id
        LEFT JOIN fares f ON t.trip_id = f.trip_id
        WHERE t.trip_status IN ('PUBLISHED', 'SCHEDULED')
        ORDER BY t.departure_time ASC
        LIMIT 6
    """)

    # Recent bookings (Multi-table Join)
    recent_bookings = query_db("""
        SELECT 
            bk.booking_id, bk.booking_reference, p.name AS passenger_name,
            r.route_name, s.seat_number, bk.total_amount, bk.booking_status,
            bk.booking_time
        FROM bookings bk
        JOIN passengers p ON bk.passenger_id = p.passenger_id
        JOIN trips t ON bk.trip_id = t.trip_id
        JOIN routes r ON t.route_id = r.route_id
        JOIN seats s ON bk.seat_id = s.seat_id
        ORDER BY bk.booking_time DESC
        LIMIT 6
    """)

    # Recent cancellations
    recent_cancellations = query_db("""
        SELECT 
            c.cancellation_id, bk.booking_reference, p.name AS passenger_name,
            c.cancellation_time, c.refund_amount, c.reason
        FROM cancellations c
        JOIN bookings bk ON c.booking_id = bk.booking_id
        JOIN passengers p ON bk.passenger_id = p.passenger_id
        ORDER BY c.cancellation_time DESC
        LIMIT 5
    """)

    # Route performance leaderboard
    top_routes = query_db("""
        SELECT route_name, total_trips, confirmed_bookings, net_revenue
        FROM route_revenue_view
        ORDER BY net_revenue DESC
        LIMIT 5
    """)

    return render_template(
        'dashboard.html',
        total_buses=total_buses,
        active_trips=active_trips,
        total_passengers=total_passengers,
        total_bookings=total_bookings,
        net_revenue=net_revenue,
        utilization_stat=utilization_stat,
        upcoming_trips=upcoming_trips,
        recent_bookings=recent_bookings,
        recent_cancellations=recent_cancellations,
        top_routes=top_routes
    )

# -----------------------------------------------------------------------------
# BUS MANAGEMENT (CRUD)
# -----------------------------------------------------------------------------
@app.route('/buses')
@login_required
def buses():
    """List fleet buses with capacity and utilization statistics."""
    fleet = query_db("""
        SELECT 
            b.bus_id, b.registration_number, b.bus_number, b.bus_type,
            b.total_seats, b.status,
            COUNT(DISTINCT t.trip_id) AS trips_count,
            COUNT(DISTINCT s.seat_id) AS seats_created
        FROM buses b
        LEFT JOIN trips t ON b.bus_id = t.bus_id
        LEFT JOIN seats s ON b.bus_id = s.bus_id
        GROUP BY b.bus_id, b.registration_number, b.bus_number, b.bus_type, b.total_seats, b.status
        ORDER BY b.bus_id ASC
    """)
    return render_template('buses.html', buses=fleet)

@app.route('/buses/add', methods=['POST'])
@login_required
def add_bus():
    """Add a new bus and automatically instantiate seat inventory."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        reg_num = request.form['registration_number'].strip().upper()
        bus_num = request.form['bus_number'].strip().upper()
        bus_type = request.form['bus_type']
        total_seats = int(request.form['total_seats'])
        status = request.form.get('status', 'ACTIVE')

        # Insert bus
        cursor.execute("""
            INSERT INTO buses (registration_number, bus_number, bus_type, total_seats, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (reg_num, bus_num, bus_type, total_seats, status))
        bus_id = cursor.lastrowid

        # Automatically populate standard seat inventory for the bus
        seat_values = []
        if 'Sleeper' in bus_type:
            half = total_seats // 2
            for i in range(1, half + 1):
                stype = 'SLEEPER_LOWER' if i % 2 != 0 else 'WINDOW'
                seat_values.append((bus_id, f"L{i:02d}", stype, 'LOWER'))
            for i in range(1, (total_seats - half) + 1):
                stype = 'SLEEPER_UPPER' if i % 2 != 0 else 'WINDOW'
                seat_values.append((bus_id, f"U{i:02d}", stype, 'UPPER'))
        else:
            for i in range(1, total_seats + 1):
                stype = 'WINDOW' if (i % 4 == 1 or i % 4 == 0) else 'AISLE'
                seat_values.append((bus_id, f"S{i:02d}", stype, 'LOWER'))

        cursor.executemany("""
            INSERT INTO seats (bus_id, seat_number, seat_type, deck)
            VALUES (%s, %s, %s, %s)
        """, seat_values)

        conn.commit()
        flash(f"Bus {bus_num} ({reg_num}) registered with {len(seat_values)} seats successfully!", 'success')
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f"Database error registering bus: {err.msg}", 'danger')
    finally:
        cursor.close()
    return redirect(url_for('buses'))

@app.route('/buses/edit/<int:bus_id>', methods=['POST'])
@login_required
def edit_bus(bus_id):
    """Modify bus attributes and operational status."""
    try:
        status = request.form['status']
        bus_type = request.form['bus_type']
        query_db("""
            UPDATE buses
            SET status = %s, bus_type = %s
            WHERE bus_id = %s
        """, (status, bus_type, bus_id), commit=True)
        flash(f"Bus ID {bus_id} updated successfully.", 'success')
    except Exception as e:
        flash(f"Error updating bus: {str(e)}", 'danger')
    return redirect(url_for('buses'))

@app.route('/buses/delete/<int:bus_id>', methods=['POST'])
@login_required
def delete_bus(bus_id):
    """Safely delete or deactivate a bus while checking foreign key constraints."""
    try:
        # Check active trips referencing this bus
        active = query_db("""
            SELECT COUNT(*) AS cnt FROM trips 
            WHERE bus_id = %s AND trip_status IN ('SCHEDULED', 'PUBLISHED')
        """, (bus_id,), one=True)
        
        if active and active['cnt'] > 0:
            flash(f"Cannot delete Bus ID {bus_id}: Active trips are scheduled on this bus. Deactivate it instead.", 'warning')
            return redirect(url_for('buses'))

        # If trips exist in past, change status to INACTIVE to maintain referential integrity
        past_trips = query_db("SELECT COUNT(*) AS cnt FROM trips WHERE bus_id = %s", (bus_id,), one=True)
        if past_trips and past_trips['cnt'] > 0:
            query_db("UPDATE buses SET status = 'INACTIVE' WHERE bus_id = %s", (bus_id,), commit=True)
            flash(f"Bus ID {bus_id} has historical trips. Status changed to INACTIVE to preserve integrity.", 'info')
        else:
            query_db("DELETE FROM buses WHERE bus_id = %s", (bus_id,), commit=True)
            flash(f"Bus ID {bus_id} and its seats deleted successfully.", 'success')
    except Exception as e:
        flash(f"Database error deleting bus: {str(e)}", 'danger')
    return redirect(url_for('buses'))

# -----------------------------------------------------------------------------
# ROUTE & STOP MANAGEMENT (CRUD & M:N JUNCTION)
# -----------------------------------------------------------------------------
@app.route('/routes')
@login_required
def routes():
    """List routes and their intermediate stops."""
    route_list = query_db("""
        SELECT 
            r.route_id, r.route_name, r.source, r.destination,
            r.distance_km, r.estimated_duration_hours,
            COUNT(DISTINCT rs.stop_id) AS stops_count,
            COUNT(DISTINCT t.trip_id) AS trips_count
        FROM routes r
        LEFT JOIN route_stops rs ON r.route_id = rs.route_id
        LEFT JOIN trips t ON r.route_id = t.route_id
        GROUP BY r.route_id, r.route_name, r.source, r.destination, r.distance_km, r.estimated_duration_hours
        ORDER BY r.route_id ASC
    """)
    all_stops = query_db("SELECT stop_id, stop_name, city FROM stops ORDER BY city, stop_name")
    return render_template('routes.html', routes=route_list, all_stops=all_stops)

@app.route('/routes/add', methods=['POST'])
@login_required
def add_route():
    """Create a new route."""
    try:
        route_name = request.form['route_name'].strip()
        source = request.form['source'].strip()
        destination = request.form['destination'].strip()
        distance = float(request.form['distance_km'])
        duration = float(request.form.get('estimated_duration_hours', 8.0))

        if source.lower() == destination.lower():
            flash('Source and destination cannot be identical.', 'danger')
            return redirect(url_for('routes'))

        query_db("""
            INSERT INTO routes (route_name, source, destination, distance_km, estimated_duration_hours)
            VALUES (%s, %s, %s, %s, %s)
        """, (route_name, source, destination, distance, duration), commit=True)
        flash(f"Route '{route_name}' added successfully!", 'success')
    except mysql.connector.Error as err:
        flash(f"Database error adding route: {err.msg}", 'danger')
    return redirect(url_for('routes'))

@app.route('/routes/<int:route_id>/stops', methods=['GET', 'POST'])
@login_required
def route_stops(route_id):
    """Manage intermediate stops on a route (M:N relationship with sequence attributes)."""
    route = query_db("SELECT * FROM routes WHERE route_id = %s", (route_id,), one=True)
    if not route:
        flash('Route not found.', 'danger')
        return redirect(url_for('routes'))

    if request.method == 'POST':
        # Add a stop to the route
        try:
            stop_id = int(request.form['stop_id'])
            stop_order = int(request.form['stop_order'])
            arr_offset = int(request.form.get('arrival_offset_mins', 0))
            dep_offset = int(request.form.get('departure_offset_mins', arr_offset))

            query_db("""
                INSERT INTO route_stops (route_id, stop_id, stop_order, arrival_offset_mins, departure_offset_mins)
                VALUES (%s, %s, %s, %s, %s)
            """, (route_id, stop_id, stop_order, arr_offset, dep_offset), commit=True)
            flash('Stop successfully linked to route!', 'success')
        except mysql.connector.Error as err:
            flash(f"Database error adding stop to route: {err.msg}", 'danger')

    assigned_stops = query_db("""
        SELECT 
            rs.route_id, rs.stop_id, rs.stop_order,
            rs.arrival_offset_mins, rs.departure_offset_mins,
            s.stop_name, s.city, s.location_landmark
        FROM route_stops rs
        JOIN stops s ON rs.stop_id = s.stop_id
        WHERE rs.route_id = %s
        ORDER BY rs.stop_order ASC
    """, (route_id,))

    available_stops = query_db("""
        SELECT stop_id, stop_name, city 
        FROM stops 
        WHERE stop_id NOT IN (SELECT stop_id FROM route_stops WHERE route_id = %s)
        ORDER BY city, stop_name
    """, (route_id,))

    return render_template(
        'route_stops.html',
        route=route,
        assigned_stops=assigned_stops,
        available_stops=available_stops
    )

@app.route('/routes/<int:route_id>/stops/delete/<int:stop_id>', methods=['POST'])
@login_required
def delete_route_stop(route_id, stop_id):
    """Remove a stop from a route."""
    try:
        query_db("DELETE FROM route_stops WHERE route_id = %s AND stop_id = %s", (route_id, stop_id), commit=True)
        flash('Stop unlinked from route.', 'info')
    except Exception as e:
        flash(f"Error removing stop: {str(e)}", 'danger')
    return redirect(url_for('route_stops', route_id=route_id))

@app.route('/stops')
@login_required
def stops():
    """List and manage master stops."""
    stop_list = query_db("""
        SELECT 
            s.stop_id, s.stop_name, s.city, s.location_landmark,
            COUNT(rs.route_id) AS routes_count
        FROM stops s
        LEFT JOIN route_stops rs ON s.stop_id = rs.stop_id
        GROUP BY s.stop_id, s.stop_name, s.city, s.location_landmark
        ORDER BY s.city ASC, s.stop_name ASC
    """)
    return render_template('stops.html', stops=stop_list)

@app.route('/stops/add', methods=['POST'])
@login_required
def add_stop():
    """Add a new stop to master catalog."""
    try:
        stop_name = request.form['stop_name'].strip()
        city = request.form['city'].strip()
        landmark = request.form.get('location_landmark', '').strip()

        query_db("""
            INSERT INTO stops (stop_name, city, location_landmark)
            VALUES (%s, %s, %s)
        """, (stop_name, city, landmark), commit=True)
        flash(f"Stop '{stop_name}' ({city}) registered successfully!", 'success')
    except mysql.connector.Error as err:
        flash(f"Database error adding stop: {err.msg}", 'danger')
    return redirect(url_for('stops'))

# -----------------------------------------------------------------------------
# TRIP MANAGEMENT
# -----------------------------------------------------------------------------
@app.route('/trips')
@login_required
def trips():
    """List trips with route details, occupancy, fare, and crew."""
    trips_list = query_db("""
        SELECT 
            t.trip_id, t.departure_time, t.arrival_time, t.trip_status,
            r.route_name, r.source, r.destination,
            b.bus_number, b.bus_type, b.total_seats,
            f.amount AS fare,
            COUNT(CASE WHEN bk.booking_status = 'CONFIRMED' THEN bk.booking_id END) AS booked_seats,
            d.name AS driver_name,
            c.name AS conductor_name
        FROM trips t
        JOIN routes r ON t.route_id = r.route_id
        JOIN buses b ON t.bus_id = b.bus_id
        LEFT JOIN fares f ON t.trip_id = f.trip_id
        LEFT JOIN bookings bk ON t.trip_id = bk.trip_id
        LEFT JOIN crew_assignments ca ON t.trip_id = ca.trip_id
        LEFT JOIN drivers d ON ca.driver_id = d.driver_id
        LEFT JOIN conductors c ON ca.conductor_id = c.conductor_id
        GROUP BY t.trip_id, t.departure_time, t.arrival_time, t.trip_status,
                 r.route_name, r.source, r.destination,
                 b.bus_number, b.bus_type, b.total_seats, f.amount,
                 d.name, c.name
        ORDER BY t.departure_time DESC
    """)

    buses_available = query_db("SELECT bus_id, bus_number, bus_type, total_seats FROM buses WHERE status = 'ACTIVE'")
    routes_available = query_db("SELECT route_id, route_name, source, destination, estimated_duration_hours FROM routes")
    drivers_available = query_db("SELECT driver_id, name, phone FROM drivers WHERE status = 'ACTIVE'")
    conductors_available = query_db("SELECT conductor_id, name, phone FROM conductors WHERE status = 'ACTIVE'")

    return render_template(
        'trips.html',
        trips=trips_list,
        buses=buses_available,
        routes=routes_available,
        drivers=drivers_available,
        conductors=conductors_available
    )

@app.route('/trips/add', methods=['POST'])
@login_required
def add_trip():
    """Schedule and initialize a trip within a transactional boundary."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        bus_id = int(request.form['bus_id'])
        route_id = int(request.form['route_id'])
        dep_str = request.form['departure_time']
        arr_str = request.form['arrival_time']
        fare_amt = float(request.form['fare_amount'])
        status = request.form.get('trip_status', 'SCHEDULED')
        driver_id = request.form.get('driver_id')
        conductor_id = request.form.get('conductor_id')

        # Format datetimes
        dep_time = datetime.fromisoformat(dep_str)
        arr_time = datetime.fromisoformat(arr_str)

        # Validation Rule 4: Departure must be before Arrival
        if dep_time >= arr_time:
            flash('Validation error: Departure time must be earlier than arrival time.', 'danger')
            return redirect(url_for('trips'))

        # Insert Trip (Database trigger trg_prevent_bus_overlap will guard overlapping bus schedules!)
        cursor.execute("""
            INSERT INTO trips (bus_id, route_id, departure_time, arrival_time, trip_status)
            VALUES (%s, %s, %s, %s, %s)
        """, (bus_id, route_id, dep_time, arr_time, status))
        trip_id = cursor.lastrowid

        # Insert Fare
        cursor.execute("""
            INSERT INTO fares (trip_id, amount)
            VALUES (%s, %s)
        """, (trip_id, fare_amt))

        # Assign Crew if selected (Database triggers guard overlapping driver/conductor schedules!)
        if driver_id and conductor_id and driver_id != '' and conductor_id != '':
            cursor.execute("""
                INSERT INTO crew_assignments (trip_id, driver_id, conductor_id)
                VALUES (%s, %s, %s)
            """, (trip_id, int(driver_id), int(conductor_id)))

        conn.commit()
        flash(f"Trip #{trip_id} scheduled successfully with fare Rs. {fare_amt:.2f}!", 'success')
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f"Database rejection: {err.msg}", 'danger')
    except Exception as e:
        conn.rollback()
        flash(f"Error creating trip: {str(e)}", 'danger')
    finally:
        cursor.close()
    return redirect(url_for('trips'))

@app.route('/trips/<int:trip_id>/status', methods=['POST'])
@login_required
def update_trip_status(trip_id):
    """Publish, complete, or cancel a trip schedule."""
    new_status = request.form['trip_status']
    try:
        query_db("UPDATE trips SET trip_status = %s WHERE trip_id = %s", (new_status, trip_id), commit=True)
        flash(f"Trip #{trip_id} status updated to {new_status}.", 'success')
    except Exception as e:
        flash(f"Database error updating trip: {str(e)}", 'danger')
    return redirect(url_for('trips'))

# -----------------------------------------------------------------------------
# CREW MANAGEMENT
# -----------------------------------------------------------------------------
@app.route('/crew')
@login_required
def crew():
    """Crew management: drivers, conductors, and roster assignments."""
    drivers_list = query_db("""
        SELECT 
            d.driver_id, d.name, d.phone, d.license_number, d.experience_years, d.status,
            COUNT(DISTINCT ca.trip_id) AS trips_count
        FROM drivers d
        LEFT JOIN crew_assignments ca ON d.driver_id = ca.driver_id
        GROUP BY d.driver_id, d.name, d.phone, d.license_number, d.experience_years, d.status
        ORDER BY d.driver_id ASC
    """)
    conductors_list = query_db("""
        SELECT 
            c.conductor_id, c.name, c.phone, c.employee_code, c.status,
            COUNT(DISTINCT ca.trip_id) AS trips_count
        FROM conductors c
        LEFT JOIN crew_assignments ca ON c.conductor_id = ca.conductor_id
        GROUP BY c.conductor_id, c.name, c.phone, c.employee_code, c.status
        ORDER BY c.conductor_id ASC
    """)
    assignments = query_db("SELECT * FROM crew_schedule_view ORDER BY departure_time DESC LIMIT 20")
    unassigned_trips = query_db("""
        SELECT t.trip_id, r.route_name, t.departure_time, b.bus_number
        FROM trips t
        JOIN routes r ON t.route_id = r.route_id
        JOIN buses b ON t.bus_id = b.bus_id
        WHERE t.trip_id NOT IN (SELECT trip_id FROM crew_assignments)
          AND t.trip_status IN ('SCHEDULED', 'PUBLISHED')
        ORDER BY t.departure_time ASC
    """)

    return render_template(
        'crew.html',
        drivers=drivers_list,
        conductors=conductors_list,
        assignments=assignments,
        unassigned_trips=unassigned_trips
    )

@app.route('/crew/drivers/add', methods=['POST'])
@login_required
def add_driver():
    """Register a new certified driver."""
    try:
        name = request.form['name'].strip()
        phone = request.form['phone'].strip()
        license_num = request.form['license_number'].strip().upper()
        exp = int(request.form.get('experience_years', 1))

        query_db("""
            INSERT INTO drivers (name, phone, license_number, experience_years, status)
            VALUES (%s, %s, %s, %s, 'ACTIVE')
        """, (name, phone, license_num, exp), commit=True)
        flash(f"Driver '{name}' enrolled successfully!", 'success')
    except mysql.connector.Error as err:
        flash(f"Database error registering driver: {err.msg}", 'danger')
    return redirect(url_for('crew'))

@app.route('/crew/conductors/add', methods=['POST'])
@login_required
def add_conductor():
    """Register a new conductor."""
    try:
        name = request.form['name'].strip()
        phone = request.form['phone'].strip()
        code = request.form['employee_code'].strip().upper()

        query_db("""
            INSERT INTO conductors (name, phone, employee_code, status)
            VALUES (%s, %s, %s, 'ACTIVE')
        """, (name, phone, code), commit=True)
        flash(f"Conductor '{name}' enrolled successfully!", 'success')
    except mysql.connector.Error as err:
        flash(f"Database error registering conductor: {err.msg}", 'danger')
    return redirect(url_for('crew'))

@app.route('/crew/assign', methods=['POST'])
@login_required
def assign_crew():
    """Assign crew to trip with trigger-enforced schedule conflict verification."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        trip_id = int(request.form['trip_id'])
        driver_id = int(request.form['driver_id'])
        conductor_id = int(request.form['conductor_id'])

        cursor.execute("""
            INSERT INTO crew_assignments (trip_id, driver_id, conductor_id)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE driver_id = VALUES(driver_id), conductor_id = VALUES(conductor_id)
        """, (trip_id, driver_id, conductor_id))
        conn.commit()
        flash(f"Crew successfully rostered for Trip #{trip_id}!", 'success')
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f"Crew conflict prevented: {err.msg}", 'danger')
    finally:
        cursor.close()
    return redirect(url_for('crew'))

# -----------------------------------------------------------------------------
# PASSENGER MANAGEMENT
# -----------------------------------------------------------------------------
@app.route('/passengers')
@login_required
def passengers():
    """List passengers with search query capability."""
    search_q = request.args.get('q', '').strip()
    if search_q:
        passenger_list = query_db("""
            SELECT 
                p.passenger_id, p.name, p.phone, p.email, p.gender, p.age,
                COUNT(bk.booking_id) AS total_bookings
            FROM passengers p
            LEFT JOIN bookings bk ON p.passenger_id = bk.passenger_id
            WHERE p.name LIKE %s OR p.phone LIKE %s OR p.email LIKE %s
            GROUP BY p.passenger_id, p.name, p.phone, p.email, p.gender, p.age
            ORDER BY p.name ASC
        """, (f"%{search_q}%", f"%{search_q}%", f"%{search_q}%"))
    else:
        passenger_list = query_db("""
            SELECT 
                p.passenger_id, p.name, p.phone, p.email, p.gender, p.age,
                COUNT(bk.booking_id) AS total_bookings
            FROM passengers p
            LEFT JOIN bookings bk ON p.passenger_id = bk.passenger_id
            GROUP BY p.passenger_id, p.name, p.phone, p.email, p.gender, p.age
            ORDER BY p.passenger_id DESC
            LIMIT 50
        """)
    return render_template('passengers.html', passengers=passenger_list, search_query=search_q)

@app.route('/passengers/add', methods=['POST'])
@login_required
def add_passenger():
    """Register passenger details."""
    try:
        name = request.form['name'].strip()
        phone = request.form['phone'].strip()
        email = request.form['email'].strip()
        gender = request.form.get('gender', 'MALE')
        age = int(request.form['age'])

        query_db("""
            INSERT INTO passengers (name, phone, email, gender, age)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, phone, email, gender, age), commit=True)
        flash(f"Passenger '{name}' created successfully!", 'success')
    except mysql.connector.Error as err:
        flash(f"Database error registering passenger: {err.msg}", 'danger')
    return redirect(url_for('passengers'))

@app.route('/passengers/<int:passenger_id>/history')
@login_required
def passenger_history(passenger_id):
    """View detailed booking history of a passenger from database view."""
    passenger = query_db("SELECT * FROM passengers WHERE passenger_id = %s", (passenger_id,), one=True)
    if not passenger:
        flash('Passenger not found.', 'danger')
        return redirect(url_for('passengers'))

    history = query_db("""
        SELECT * FROM passenger_booking_history
        WHERE passenger_id = %s
        ORDER BY booking_time DESC
    """, (passenger_id,))

    return render_template('passenger_history.html', passenger=passenger, history=history)

# -----------------------------------------------------------------------------
# SEARCH & AVAILABILITY ENGINE
# -----------------------------------------------------------------------------
@app.route('/search')
def search():
    """Search for trip availability by origin, destination, and travel date."""
    source = request.args.get('source', '').strip()
    destination = request.args.get('destination', '').strip()
    travel_date = request.args.get('travel_date', '').strip()

    cities = query_db("SELECT DISTINCT city FROM stops ORDER BY city")

    trips = []
    if source or destination or travel_date:
        query_conditions = ["t.trip_status = 'PUBLISHED'"]
        params = []

        if source:
            query_conditions.append("r.source LIKE %s")
            params.append(f"%{source}%")
        if destination:
            query_conditions.append("r.destination LIKE %s")
            params.append(f"%{destination}%")
        if travel_date:
            query_conditions.append("DATE(t.departure_time) = %s")
            params.append(travel_date)

        where_clause = " AND ".join(query_conditions)
        trips = query_db(f"""
            SELECT 
                t.trip_id, r.route_name, r.source, r.destination, r.distance_km,
                b.bus_number, b.bus_type, b.total_seats,
                (b.total_seats - COALESCE(bkg.cnt, 0)) AS available_seats,
                f.amount AS fare,
                t.departure_time, t.arrival_time, t.trip_status
            FROM trips t
            JOIN routes r ON t.route_id = r.route_id
            JOIN buses b ON t.bus_id = b.bus_id
            LEFT JOIN fares f ON t.trip_id = f.trip_id
            LEFT JOIN (
                SELECT trip_id, COUNT(*) AS cnt 
                FROM bookings 
                WHERE booking_status = 'CONFIRMED' 
                GROUP BY trip_id
            ) bkg ON t.trip_id = bkg.trip_id
            WHERE {where_clause}
            ORDER BY t.departure_time ASC
        """, tuple(params))

    return render_template(
        'search.html',
        cities=cities,
        trips=trips,
        selected_source=source,
        selected_destination=destination,
        selected_date=travel_date
    )

# -----------------------------------------------------------------------------
# INTERACTIVE SEAT BOOKING & TRANSACTION WORKFLOW
# -----------------------------------------------------------------------------
@app.route('/book/<int:trip_id>')
def book_seat_page(trip_id):
    """Visual seat map and reservation interface for a trip."""
    trip = query_db("""
        SELECT 
            t.trip_id, t.bus_id, t.departure_time, t.arrival_time, t.trip_status,
            r.route_name, r.source, r.destination, r.distance_km,
            b.bus_number, b.bus_type, b.total_seats,
            COALESCE(f.amount, 0.0) AS fare
        FROM trips t
        JOIN routes r ON t.route_id = r.route_id
        JOIN buses b ON t.bus_id = b.bus_id
        LEFT JOIN fares f ON t.trip_id = f.trip_id
        WHERE t.trip_id = %s
    """, (trip_id,), one=True)

    if not trip:
        flash('Trip not found.', 'danger')
        return redirect(url_for('search'))

    if trip['trip_status'] not in ('PUBLISHED', 'SCHEDULED'):
        flash('This trip is not open for reservations.', 'warning')
        return redirect(url_for('search'))

    # Load all seats for this trip's bus
    seats = query_db("""
        SELECT 
            s.seat_id, s.seat_number, s.seat_type, s.deck,
            CASE WHEN bk.booking_id IS NOT NULL THEN 1 ELSE 0 END AS is_booked
        FROM seats s
        LEFT JOIN bookings bk ON s.seat_id = bk.seat_id 
                              AND bk.trip_id = %s 
                              AND bk.booking_status = 'CONFIRMED'
        WHERE s.bus_id = %s
        ORDER BY s.deck ASC, s.seat_number ASC
    """, (trip_id, trip['bus_id']))

    # Existing passengers for quick dropdown selection
    passengers_list = query_db("SELECT passenger_id, name, phone, email FROM passengers ORDER BY name ASC")

    return render_template(
        'seat_layout.html',
        trip=trip,
        seats=seats,
        passengers=passengers_list
    )

@app.route('/book/<int:trip_id>/confirm', methods=['POST'])
def confirm_booking(trip_id):
    """
    ACID TRANSACTION WORKFLOW:
    Step 1: BEGIN TRANSACTION
    Step 2: Check whether trip exists and is bookable
    Step 3: Check whether seat belongs to trip's bus
    Step 4: Check whether seat is already booked (lock check)
    Step 5: Retrieve or verify fare
    Step 6: Insert or resolve passenger record
    Step 7: Insert booking record
    Step 8: Insert payment record
    Step 9: COMMIT
    If any error occurs: ROLLBACK
    """
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        seat_id = int(request.form['seat_id'])
        payment_method = request.form.get('payment_method', 'UPI')
        passenger_mode = request.form.get('passenger_mode', 'existing')

        # 1. Verify trip existence and status
        cursor.execute("""
            SELECT t.trip_id, t.bus_id, t.trip_status, t.departure_time, f.amount AS fare
            FROM trips t
            LEFT JOIN fares f ON t.trip_id = f.trip_id
            WHERE t.trip_id = %s
        """, (trip_id,))
        trip = cursor.fetchone()

        if not trip:
            raise Exception("Trip not found.")
        if trip['trip_status'] not in ('PUBLISHED', 'SCHEDULED'):
            raise Exception("Trip is not currently open for bookings.")

        fare_amount = float(trip['fare'] or 0.0)

        # 2. Verify seat belongs to the bus
        cursor.execute("SELECT bus_id, seat_number FROM seats WHERE seat_id = %s", (seat_id,))
        seat = cursor.fetchone()
        if not seat or seat['bus_id'] != trip['bus_id']:
            raise Exception("Seat does not belong to the bus assigned to this trip.")

        # 3. Check if seat is already booked (Transaction isolation)
        cursor.execute("""
            SELECT booking_id FROM bookings
            WHERE trip_id = %s AND seat_id = %s AND booking_status = 'CONFIRMED'
            FOR UPDATE
        """, (trip_id, seat_id))
        existing_booking = cursor.fetchone()
        if existing_booking:
            raise Exception(f"Seat {seat['seat_number']} is already booked for this trip.")

        # 4. Resolve passenger
        if passenger_mode == 'new':
            p_name = request.form['name'].strip()
            p_phone = request.form['phone'].strip()
            p_email = request.form['email'].strip()
            p_gender = request.form.get('gender', 'MALE')
            p_age = int(request.form.get('age', 25))

            # Insert or fetch passenger
            cursor.execute("""
                INSERT INTO passengers (name, phone, email, gender, age)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE name = VALUES(name), age = VALUES(age)
            """, (p_name, p_phone, p_email, p_gender, p_age))
            
            cursor.execute("SELECT passenger_id FROM passengers WHERE phone = %s", (p_phone,))
            passenger_id = cursor.fetchone()['passenger_id']
        else:
            passenger_id = int(request.form['passenger_id'])

        # 5. Insert Booking record
        bkg_ref = f"BKG-{uuid.uuid4().hex[:8].upper()}"
        cursor.execute("""
            INSERT INTO bookings (booking_reference, trip_id, passenger_id, seat_id, booking_time, booking_status, total_amount)
            VALUES (%s, %s, %s, %s, NOW(), 'CONFIRMED', %s)
        """, (bkg_ref, trip_id, passenger_id, seat_id, fare_amount))
        booking_id = cursor.lastrowid

        # 6. Insert Payment record
        txn_ref = f"TXN-{uuid.uuid4().hex[:10].upper()}"
        cursor.execute("""
            INSERT INTO payments (booking_id, amount, payment_method, payment_status, payment_time, transaction_reference)
            VALUES (%s, %s, %s, 'PAID', NOW(), %s)
        """, (booking_id, fare_amount, payment_method, txn_ref))

        # 7. Atomically Commit the Transaction
        conn.commit()
        flash(f"Booking confirmed successfully! Reference: {bkg_ref}", 'success')
        return redirect(url_for('booking_ticket', booking_id=booking_id))

    except Exception as e:
        conn.rollback()
        flash(f"Transaction failed. No changes were made: {str(e)}", 'danger')
        return redirect(url_for('book_seat_page', trip_id=trip_id))
    finally:
        cursor.close()

# -----------------------------------------------------------------------------
# BOOKINGS & TICKET RECEIPT
# -----------------------------------------------------------------------------
@app.route('/bookings')
@login_required
def bookings():
    """List all reservations with passenger, trip, and payment statuses."""
    status_filter = request.args.get('status', 'ALL')
    
    where = ""
    params = []
    if status_filter in ('CONFIRMED', 'CANCELLED'):
        where = "WHERE bk.booking_status = %s"
        params.append(status_filter)

    bookings_list = query_db(f"""
        SELECT 
            bk.booking_id, bk.booking_reference, bk.booking_time, bk.booking_status,
            bk.total_amount,
            p.passenger_id, p.name AS passenger_name, p.phone AS passenger_phone,
            r.route_name, r.source, r.destination,
            t.trip_id, t.departure_time,
            b.bus_number,
            s.seat_number,
            pm.payment_method, pm.payment_status, pm.transaction_reference,
            c.refund_amount
        FROM bookings bk
        JOIN passengers p ON bk.passenger_id = p.passenger_id
        JOIN trips t ON bk.trip_id = t.trip_id
        JOIN routes r ON t.route_id = r.route_id
        JOIN buses b ON t.bus_id = b.bus_id
        JOIN seats s ON bk.seat_id = s.seat_id
        LEFT JOIN payments pm ON bk.booking_id = pm.booking_id
        LEFT JOIN cancellations c ON bk.booking_id = c.booking_id
        {where}
        ORDER BY bk.booking_time DESC
    """, tuple(params))

    return render_template('bookings.html', bookings=bookings_list, current_status=status_filter)

@app.route('/bookings/<int:booking_id>/ticket')
def booking_ticket(booking_id):
    """Display printable boarding ticket confirmation."""
    ticket = query_db("""
        SELECT 
            bk.booking_id, bk.booking_reference, bk.booking_time, bk.booking_status,
            bk.total_amount,
            p.name AS passenger_name, p.phone AS passenger_phone, p.email AS passenger_email,
            p.gender, p.age,
            r.route_name, r.source, r.destination, r.distance_km,
            t.trip_id, t.departure_time, t.arrival_time,
            b.bus_number, b.bus_type, b.registration_number,
            s.seat_number, s.seat_type, s.deck,
            pm.payment_method, pm.payment_status, pm.transaction_reference, pm.payment_time,
            c.cancellation_time, c.refund_amount, c.reason
        FROM bookings bk
        JOIN passengers p ON bk.passenger_id = p.passenger_id
        JOIN trips t ON bk.trip_id = t.trip_id
        JOIN routes r ON t.route_id = r.route_id
        JOIN buses b ON t.bus_id = b.bus_id
        JOIN seats s ON bk.seat_id = s.seat_id
        LEFT JOIN payments pm ON bk.booking_id = pm.booking_id
        LEFT JOIN cancellations c ON bk.booking_id = c.booking_id
        WHERE bk.booking_id = %s
    """, (booking_id,), one=True)

    if not ticket:
        flash('Ticket not found.', 'danger')
        return redirect(url_for('bookings'))

    return render_template('ticket.html', ticket=ticket)

# -----------------------------------------------------------------------------
# CANCELLATION ENGINE
# -----------------------------------------------------------------------------
@app.route('/cancellations')
@login_required
def cancellations():
    """List cancellation audit logs and refund disbursements."""
    records = query_db("SELECT * FROM cancellation_report_view ORDER BY cancellation_time DESC")
    return render_template('cancellations.html', cancellations=records)

@app.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    """
    Cancel booking with transactional refund policy calculation:
    - Departure > 24 hours away: 100% refund
    - Departure 12 - 24 hours away: 75% refund
    - Departure < 12 hours away: 50% refund
    Updates booking and payment state atomically.
    """
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        reason = request.form.get('reason', 'Passenger requested cancellation').strip()

        # Step 1: Query booking and departure time
        cursor.execute("""
            SELECT bk.booking_id, bk.booking_status, bk.total_amount, t.departure_time
            FROM bookings bk
            JOIN trips t ON bk.trip_id = t.trip_id
            WHERE bk.booking_id = %s
        """, (booking_id,))
        booking = cursor.fetchone()

        if not booking:
            raise Exception("Booking record not found.")

        if booking['booking_status'] == 'CANCELLED':
            raise Exception("Booking has already been cancelled.")

        # Step 2: Calculate refund percentage based on business policy
        now = datetime.now()
        dep_time = booking['departure_time']
        hours_before = (dep_time - now).total_seconds() / 3600.0

        if hours_before >= 24.0:
            refund_pct = 100.00
        elif hours_before >= 12.0:
            refund_pct = 75.00
        elif hours_before > 0:
            refund_pct = 50.00
        else:
            refund_pct = 0.00  # Departed trips yield zero refund

        total_fare = float(booking['total_amount'])
        refund_amount = round(total_fare * (refund_pct / 100.0), 2)

        # Step 3: Insert into cancellations table
        # Triggers trg_validate_cancellation and trg_after_cancellation_sync execute automatically!
        cursor.execute("""
            INSERT INTO cancellations (booking_id, cancellation_time, reason, refund_percentage, refund_amount)
            VALUES (%s, NOW(), %s, %s, %s)
        """, (booking_id, reason, refund_pct, refund_amount))

        conn.commit()
        flash(f"Booking #{booking_id} cancelled. Refund of Rs. {refund_amount:.2f} ({refund_pct}%) approved.", 'info')
    except Exception as e:
        conn.rollback()
        flash(f"Cancellation rejected: {str(e)}", 'danger')
    finally:
        cursor.close()

    return redirect(url_for('bookings'))

# -----------------------------------------------------------------------------
# PAYMENTS LEDGER
# -----------------------------------------------------------------------------
@app.route('/payments')
@login_required
def payments():
    """Financial settlement audit ledger."""
    payments_list = query_db("""
        SELECT 
            pm.payment_id, pm.transaction_reference, pm.amount,
            pm.payment_method, pm.payment_status, pm.payment_time,
            bk.booking_reference,
            p.name AS passenger_name,
            r.route_name
        FROM payments pm
        JOIN bookings bk ON pm.booking_id = bk.booking_id
        JOIN passengers p ON bk.passenger_id = p.passenger_id
        JOIN trips t ON bk.trip_id = t.trip_id
        JOIN routes r ON t.route_id = r.route_id
        ORDER BY pm.payment_time DESC
        LIMIT 100
    """)
    return render_template('payments.html', payments=payments_list)

# -----------------------------------------------------------------------------
# ANALYTICAL REPORTS (10 COMPREHENSIVE REPORTS)
# -----------------------------------------------------------------------------
@app.route('/reports')
@login_required
def reports():
    """Centralized DBMS reports suite utilizing complex SQL and views."""
    # 1. Trip Occupancy Report
    occupancy_report = query_db("SELECT * FROM trip_occupancy_view ORDER BY occupancy_percentage DESC LIMIT 15")

    # 2. Route Revenue Report
    route_revenue = query_db("SELECT * FROM route_revenue_view ORDER BY net_revenue DESC")

    # 3. Fleet Utilization Report
    fleet_util = query_db("SELECT * FROM fleet_utilization_view ORDER BY total_revenue_generated DESC")

    # 4. Cancellation Analysis Report
    cancellations_report = query_db("SELECT * FROM cancellation_report_view ORDER BY cancellation_time DESC")

    # 5. Crew Schedules Report
    crew_schedules = query_db("SELECT * FROM crew_schedule_view ORDER BY departure_time DESC LIMIT 15")

    # 6. Daily Revenue Trend (Aggregate GROUP BY DATE)
    daily_revenue = query_db("""
        SELECT 
            DATE(pm.payment_time) AS payment_date,
            COUNT(pm.payment_id) AS transactions_count,
            SUM(CASE WHEN pm.payment_status = 'PAID' THEN pm.amount ELSE 0 END) AS gross_daily,
            COALESCE(SUM(c.refund_amount), 0) AS refunds_daily,
            (SUM(CASE WHEN pm.payment_status = 'PAID' THEN pm.amount ELSE 0 END) - COALESCE(SUM(c.refund_amount), 0)) AS net_daily
        FROM payments pm
        LEFT JOIN cancellations c ON pm.booking_id = c.booking_id
        GROUP BY DATE(pm.payment_time)
        ORDER BY payment_date DESC
        LIMIT 10
    """)

    # 7. Popular Routes by Passenger Volume
    popular_routes = query_db("""
        SELECT 
            r.route_name, r.source, r.destination,
            COUNT(bk.booking_id) AS total_passengers,
            SUM(bk.total_amount) AS total_revenue
        FROM routes r
        JOIN trips t ON r.route_id = t.route_id
        JOIN bookings bk ON t.trip_id = bk.trip_id
        WHERE bk.booking_status = 'CONFIRMED'
        GROUP BY r.route_id, r.route_name, r.source, r.destination
        ORDER BY total_passengers DESC
    """)

    # 8. Bus Performance & Yield
    bus_performance = query_db("""
        SELECT 
            b.bus_number, b.bus_type, b.total_seats,
            COUNT(DISTINCT t.trip_id) AS total_trips,
            COUNT(bk.booking_id) AS total_bookings,
            ROUND(COUNT(bk.booking_id) / NULLIF(COUNT(DISTINCT t.trip_id) * b.total_seats, 0) * 100, 1) AS load_factor,
            SUM(bk.total_amount) AS revenue
        FROM buses b
        LEFT JOIN trips t ON b.bus_id = t.bus_id
        LEFT JOIN bookings bk ON t.trip_id = bk.trip_id AND bk.booking_status = 'CONFIRMED'
        GROUP BY b.bus_id, b.bus_number, b.bus_type, b.total_seats
        ORDER BY revenue DESC
    """)

    # 9. Payment Methods Breakdown
    payment_methods = query_db("""
        SELECT 
            payment_method,
            COUNT(*) AS transactions,
            SUM(amount) AS total_collected
        FROM payments
        WHERE payment_status = 'PAID'
        GROUP BY payment_method
        ORDER BY total_collected DESC
    """)

    # 10. Top Frequent Travellers
    top_passengers = query_db("""
        SELECT 
            p.passenger_id, p.name, p.phone, p.email,
            COUNT(bk.booking_id) AS trips_booked,
            SUM(bk.total_amount) AS total_spend
        FROM passengers p
        JOIN bookings bk ON p.passenger_id = bk.passenger_id
        WHERE bk.booking_status = 'CONFIRMED'
        GROUP BY p.passenger_id, p.name, p.phone, p.email
        ORDER BY trips_booked DESC, total_spend DESC
        LIMIT 10
    """)

    return render_template(
        'reports.html',
        occupancy_report=occupancy_report,
        route_revenue=route_revenue,
        fleet_util=fleet_util,
        cancellations_report=cancellations_report,
        crew_schedules=crew_schedules,
        daily_revenue=daily_revenue,
        popular_routes=popular_routes,
        bus_performance=bus_performance,
        payment_methods=payment_methods,
        top_passengers=top_passengers
    )

# -----------------------------------------------------------------------------
# SQL DEMONSTRATION PAGE (FOR DBMS FACULTY VIVA)
# -----------------------------------------------------------------------------
@app.route('/sql-demo')
@login_required
def sql_demo():
    """
    Demonstrates selected relational SQL concepts live against MySQL:
    Joins, Aggregations, Having, Subqueries, Exists, Case, Views.
    """
    demos = [
        {
            "id": 1,
            "concept": "Inner Join & Multiple-Table Projection",
            "description": "Joins 4 tables (trips, routes, buses, fares) to project upcoming published departures.",
            "sql": """
SELECT 
    t.trip_id,
    r.route_name,
    b.bus_number,
    b.bus_type,
    t.departure_time,
    f.amount AS fare,
    t.trip_status
FROM trips t
INNER JOIN routes r ON t.route_id = r.route_id
INNER JOIN buses b ON t.bus_id = b.bus_id
LEFT JOIN fares f ON t.trip_id = f.trip_id
WHERE t.trip_status = 'PUBLISHED'
ORDER BY t.departure_time ASC
LIMIT 6;
            """
        },
        {
            "id": 2,
            "concept": "Group By & Aggregate Functions with Having Clause",
            "description": "Aggregates revenue and passenger volumes per route, filtering for high-performing routes (HAVING gross_revenue > 2000).",
            "sql": """
SELECT 
    r.route_name,
    COUNT(DISTINCT t.trip_id) AS total_trips,
    COUNT(bk.booking_id) AS confirmed_passengers,
    SUM(bk.total_amount) AS gross_revenue,
    ROUND(AVG(bk.total_amount), 2) AS avg_fare_paid
FROM routes r
INNER JOIN trips t ON r.route_id = t.route_id
INNER JOIN bookings bk ON t.trip_id = bk.trip_id
WHERE bk.booking_status = 'CONFIRMED'
GROUP BY r.route_id, r.route_name
HAVING gross_revenue > 2000
ORDER BY gross_revenue DESC;
            """
        },
        {
            "id": 3,
            "concept": "Scalar Subquery with Average Comparison",
            "description": "Finds routes whose physical travel distance exceeds the fleet-wide average distance.",
            "sql": """
SELECT 
    route_id,
    route_name,
    source,
    destination,
    distance_km,
    (SELECT ROUND(AVG(distance_km), 2) FROM routes) AS fleet_avg_distance
FROM routes
WHERE distance_km > (SELECT AVG(distance_km) FROM routes)
ORDER BY distance_km DESC;
            """
        },
        {
            "id": 4,
            "concept": "Correlated Subquery",
            "description": "Finds trips whose confirmed booking count is strictly greater than the average booking count across all trips on that same route.",
            "sql": """
SELECT 
    t1.trip_id,
    r.route_name,
    t1.departure_time,
    (SELECT COUNT(*) FROM bookings b1 WHERE b1.trip_id = t1.trip_id AND b1.booking_status = 'CONFIRMED') AS trip_bookings
FROM trips t1
JOIN routes r ON t1.route_id = r.route_id
WHERE (
    SELECT COUNT(*) 
    FROM bookings b1 
    WHERE b1.trip_id = t1.trip_id AND b1.booking_status = 'CONFIRMED'
) > (
    SELECT AVG(route_trip_bkg.cnt)
    FROM (
        SELECT t2.trip_id, COUNT(b2.booking_id) AS cnt
        FROM trips t2
        LEFT JOIN bookings b2 ON t2.trip_id = b2.trip_id AND b2.booking_status = 'CONFIRMED'
        WHERE t2.route_id = t1.route_id
        GROUP BY t2.trip_id
    ) route_trip_bkg
)
LIMIT 8;
            """
        },
        {
            "id": 5,
            "concept": "EXISTS & NOT EXISTS Operators",
            "description": "Demonstrates existential semi-join: selects drivers who have active upcoming trip assignments.",
            "sql": """
SELECT 
    d.driver_id,
    d.name,
    d.phone,
    d.license_number,
    d.experience_years
FROM drivers d
WHERE EXISTS (
    SELECT 1 
    FROM crew_assignments ca
    JOIN trips t ON ca.trip_id = t.trip_id
    WHERE ca.driver_id = d.driver_id
      AND t.trip_status IN ('SCHEDULED', 'PUBLISHED')
);
            """
        },
        {
            "id": 6,
            "concept": "Conditional CASE Expression",
            "description": "Categorizes trips into Load Factor categories (High, Medium, Low Occupancy) dynamically.",
            "sql": """
SELECT 
    t.trip_id,
    r.route_name,
    b.bus_number,
    b.total_seats,
    COUNT(CASE WHEN bk.booking_status = 'CONFIRMED' THEN bk.booking_id END) AS booked,
    ROUND(COUNT(CASE WHEN bk.booking_status = 'CONFIRMED' THEN bk.booking_id END) * 100.0 / b.total_seats, 1) AS occ_pct,
    CASE 
        WHEN (COUNT(CASE WHEN bk.booking_status = 'CONFIRMED' THEN bk.booking_id END) * 1.0 / b.total_seats) >= 0.30 THEN 'HIGH OCCUPANCY'
        WHEN (COUNT(CASE WHEN bk.booking_status = 'CONFIRMED' THEN bk.booking_id END) * 1.0 / b.total_seats) >= 0.15 THEN 'MEDIUM OCCUPANCY'
        ELSE 'LOW OCCUPANCY'
    END AS occupancy_band
FROM trips t
JOIN routes r ON t.route_id = r.route_id
JOIN buses b ON t.bus_id = b.bus_id
LEFT JOIN bookings bk ON t.trip_id = bk.trip_id
GROUP BY t.trip_id, r.route_name, b.bus_number, b.total_seats
ORDER BY occ_pct DESC
LIMIT 8;
            """
        },
        {
            "id": 7,
            "concept": "Database View Execution (route_revenue_view)",
            "description": "Queries directly from the compiled SQL view `route_revenue_view` created in views.sql.",
            "sql": """
SELECT 
    route_name,
    source,
    destination,
    total_trips,
    confirmed_bookings,
    gross_revenue,
    total_refunds,
    net_revenue
FROM route_revenue_view
ORDER BY net_revenue DESC;
            """
        }
    ]

    # Execute all demo queries live and capture results
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    results = []
    for d in demos:
        try:
            cursor.execute(d['sql'])
            rows = cursor.fetchall()
            columns = cursor.column_names if cursor.description else []
            results.append({
                "meta": d,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "error": None
            })
        except Exception as e:
            results.append({
                "meta": d,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": str(e)
            })
    cursor.close()

    return render_template('sql_demo.html', results=results)

@app.route('/sql-demo/execute', methods=['POST'])
@login_required
def execute_custom_sql():
    """Interactive SQL query execution endpoint for faculty viva examination."""
    custom_sql = request.form.get('custom_sql', '').strip()
    
    # Security constraint: only allow read-only SELECT queries
    first_word = custom_sql.split()[0].upper() if custom_sql else ''
    if first_word not in ('SELECT', 'WITH', 'SHOW', 'EXPLAIN', 'DESCRIBE'):
        return jsonify({
            "success": False,
            "error": "Security constraint: For safety during viva, only SELECT / EXPLAIN queries are permitted."
        })

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(custom_sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        return jsonify({
            "success": True,
            "columns": columns,
            "rows": rows,
            "count": len(rows)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })
    finally:
        cursor.close()

# -----------------------------------------------------------------------------
# APPLICATION ENTRYPOINT
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 70)
    print("Starting Bus Reservation and Fleet Scheduling System")
    print(f"Connecting to MySQL: {app.config['MYSQL_HOST']}:{app.config['MYSQL_PORT']}")
    print("Web server running on http://127.0.0.1:5000")
    print("Default Admin Credentials: admin / admin123")
    print("=" * 70)
    app.run(host='0.0.0.0', port=5000, debug=True)
