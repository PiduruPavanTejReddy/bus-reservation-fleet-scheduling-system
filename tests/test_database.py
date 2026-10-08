"""
BUS RESERVATION AND FLEET SCHEDULING SYSTEM
Comprehensive Database & Business Rules Test Suite
Target DBMS: MySQL 8.0+
"""

import pytest
import mysql.connector
from datetime import datetime, timedelta
import uuid
import sys
import os

# Add parent directory to path to import config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config

@pytest.fixture(scope="module")
def db_conn():
    """Module-level database connection fixture."""
    conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        autocommit=False
    )
    yield conn
    conn.close()

# -----------------------------------------------------------------------------
# 1. BUS CONSTRAINTS TESTS
# -----------------------------------------------------------------------------
def test_valid_bus_insertion(db_conn):
    """Test inserting a valid bus record into BUSES table."""
    cursor = db_conn.cursor(dictionary=True)
    unique_reg = f"TEST-{uuid.uuid4().hex[:6].upper()}"
    unique_bus_num = f"TBUS-{uuid.uuid4().hex[:4].upper()}"
    try:
        cursor.execute("""
            INSERT INTO buses (registration_number, bus_number, bus_type, total_seats, status)
            VALUES (%s, %s, 'AC Seater', 35, 'ACTIVE')
        """, (unique_reg, unique_bus_num))
        db_conn.commit()
        bus_id = cursor.lastrowid
        assert bus_id > 0

        # Cleanup
        cursor.execute("DELETE FROM buses WHERE bus_id = %s", (bus_id,))
        db_conn.commit()
    finally:
        cursor.close()

def test_duplicate_bus_insertion_rejected(db_conn):
    """Test UNIQUE constraint on bus registration_number."""
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Existing registration number TS09UB4521 from seed data
        with pytest.raises(mysql.connector.Error) as exc_info:
            cursor.execute("""
                INSERT INTO buses (registration_number, bus_number, bus_type, total_seats, status)
                VALUES ('TS09UB4521', 'BUS-DUP', 'AC Sleeper', 30, 'ACTIVE')
            """)
        db_conn.rollback()
        assert "Duplicate entry" in str(exc_info.value)
    finally:
        cursor.close()

# -----------------------------------------------------------------------------
# 2. ROUTE CONSTRAINTS TESTS
# -----------------------------------------------------------------------------
def test_valid_route_creation(db_conn):
    """Test creating a valid travel route."""
    cursor = db_conn.cursor(dictionary=True)
    r_name = f"Test Route {uuid.uuid4().hex[:4]}"
    try:
        cursor.execute("""
            INSERT INTO routes (route_name, source, destination, distance_km, estimated_duration_hours)
            VALUES (%s, 'Hyderabad', 'Kurnool', 210.0, 3.5)
        """, (r_name,))
        db_conn.commit()
        r_id = cursor.lastrowid
        assert r_id > 0

        # Cleanup
        cursor.execute("DELETE FROM routes WHERE route_id = %s", (r_id,))
        db_conn.commit()
    finally:
        cursor.close()

def test_invalid_route_source_destination_same(db_conn):
    """Test CHECK constraint preventing identical source and destination."""
    cursor = db_conn.cursor(dictionary=True)
    try:
        with pytest.raises(mysql.connector.Error) as exc_info:
            cursor.execute("""
                INSERT INTO routes (route_name, source, destination, distance_km, estimated_duration_hours)
                VALUES ('Circular Test', 'Hyderabad', 'Hyderabad', 10.0, 1.0)
            """)
        db_conn.rollback()
        assert "chk_route_src_dst" in str(exc_info.value) or "Check constraint" in str(exc_info.value)
    finally:
        cursor.close()

# -----------------------------------------------------------------------------
# 3. TRIP SCHEDULE CONSTRAINTS TESTS
# -----------------------------------------------------------------------------
def test_invalid_trip_departure_arrival_order(db_conn):
    """Test CHECK constraint ensuring departure_time < arrival_time."""
    cursor = db_conn.cursor(dictionary=True)
    try:
        now = datetime.now()
        invalid_arr = now - timedelta(hours=2)
        with pytest.raises(mysql.connector.Error) as exc_info:
            cursor.execute("""
                INSERT INTO trips (bus_id, route_id, departure_time, arrival_time, trip_status)
                VALUES (1, 1, %s, %s, 'SCHEDULED')
            """, (now, invalid_arr))
        db_conn.rollback()
        assert "chk_trip_schedule" in str(exc_info.value) or "Check constraint" in str(exc_info.value)
    finally:
        cursor.close()

def test_overlapping_bus_trip_rejected(db_conn):
    """Test trigger trg_prevent_bus_overlap rejecting overlapping bus assignment."""
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Trip 1 operates from 2026-10-01 21:00 to 2026-10-02 06:30 on bus_id = 1
        with pytest.raises(mysql.connector.Error) as exc_info:
            cursor.execute("""
                INSERT INTO trips (bus_id, route_id, departure_time, arrival_time, trip_status)
                VALUES (1, 3, '2026-10-01 22:00:00', '2026-10-02 03:00:00', 'PUBLISHED')
            """)
        db_conn.rollback()
        assert "Bus is already assigned to an overlapping trip" in str(exc_info.value)
    finally:
        cursor.close()

# -----------------------------------------------------------------------------
# 4. CREW CONFLICT TESTS
# -----------------------------------------------------------------------------
def test_overlapping_driver_schedule_rejected(db_conn):
    """Test trigger trg_prevent_driver_overlap rejecting overlapping driver assignment."""
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Trip 11: 2026-10-08 21:00:00 to 2026-10-09 06:30:00 with driver 11
        # Create a concurrent trip on bus 3 (which is free)
        cursor.execute("""
            INSERT INTO trips (bus_id, route_id, departure_time, arrival_time, trip_status)
            VALUES (3, 3, '2026-10-08 22:00:00', '2026-10-09 03:00:00', 'PUBLISHED')
        """)
        new_trip_id = cursor.lastrowid

        # Driver 11 is already assigned to trip 11 (21:00 to 06:30)
        cursor.execute("SELECT driver_id FROM crew_assignments WHERE trip_id = 11")
        busy_driver_id = cursor.fetchone()['driver_id']

        with pytest.raises(mysql.connector.Error) as exc_info:
            cursor.execute("""
                INSERT INTO crew_assignments (trip_id, driver_id, conductor_id)
                VALUES (%s, %s, 1)
            """, (new_trip_id, busy_driver_id))
        
        db_conn.rollback()
        assert "Driver is unavailable during this time" in str(exc_info.value)
    finally:
        db_conn.rollback()
        cursor.close()

# -----------------------------------------------------------------------------
# 5. BOOKING TRANSACTION & SEAT INTEGRITY TESTS
# -----------------------------------------------------------------------------
def test_duplicate_seat_booking_rejected_by_trigger(db_conn):
    """Test trigger trg_prevent_duplicate_seat_booking preventing double booking."""
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Trip 1, Seat 1 is already CONFIRMED
        with pytest.raises(mysql.connector.Error) as exc_info:
            cursor.execute("""
                INSERT INTO bookings (booking_reference, trip_id, passenger_id, seat_id, booking_time, booking_status, total_amount)
                VALUES ('BKG-DUP-TEST', 1, 2, 1, NOW(), 'CONFIRMED', 1150.00)
            """)
        db_conn.rollback()
        assert "Seat is already booked for this trip" in str(exc_info.value)
    finally:
        cursor.close()

def test_seat_does_not_belong_to_bus_rejected(db_conn):
    """Test trigger trg_validate_seat_belongs_to_bus ensuring seat belongs to trip's bus."""
    cursor = db_conn.cursor(dictionary=True)
    try:
        # Trip 1 operates on Bus 1 (Seats 1..40). Seat 45 belongs to Bus 2!
        with pytest.raises(mysql.connector.Error) as exc_info:
            cursor.execute("""
                INSERT INTO bookings (booking_reference, trip_id, passenger_id, seat_id, booking_time, booking_status, total_amount)
                VALUES ('BKG-WRONG-SEAT', 1, 1, 45, NOW(), 'CONFIRMED', 1150.00)
            """)
        db_conn.rollback()
        assert "Seat does not belong to the bus assigned to this trip" in str(exc_info.value)
    finally:
        cursor.close()

def test_atomic_booking_transaction_commit(db_conn):
    """Test atomic reservation transaction with COMMIT."""
    cursor = db_conn.cursor(dictionary=True)
    bkg_ref = f"BKG-T-{uuid.uuid4().hex[:6].upper()}"
    txn_ref = f"TXN-T-{uuid.uuid4().hex[:6].upper()}"
    try:
        # Use Trip 31 (Bus 1, Seat 35 is currently unbooked)
        # Lock and verify
        cursor.execute("SELECT fare_id, amount FROM fares WHERE trip_id = 31")
        fare = cursor.fetchone()['amount']

        # Insert booking
        cursor.execute("""
            INSERT INTO bookings (booking_reference, trip_id, passenger_id, seat_id, booking_time, booking_status, total_amount)
            VALUES (%s, 31, 1, 35, NOW(), 'CONFIRMED', %s)
        """, (bkg_ref, fare))
        booking_id = cursor.lastrowid

        # Insert payment
        cursor.execute("""
            INSERT INTO payments (booking_id, amount, payment_method, payment_status, payment_time, transaction_reference)
            VALUES (%s, %s, 'UPI', 'PAID', NOW(), %s)
        """, (booking_id, fare, txn_ref))

        db_conn.commit()

        # Verify insertion
        cursor.execute("SELECT booking_status FROM bookings WHERE booking_id = %s", (booking_id,))
        assert cursor.fetchone()['booking_status'] == 'CONFIRMED'

        # Cleanup
        cursor.execute("DELETE FROM payments WHERE booking_id = %s", (booking_id,))
        cursor.execute("DELETE FROM bookings WHERE booking_id = %s", (booking_id,))
        db_conn.commit()
    finally:
        cursor.close()

def test_atomic_booking_transaction_rollback_on_failure(db_conn):
    """Test ACID ROLLBACK ensuring partial updates are discarded on failure."""
    cursor = db_conn.cursor(dictionary=True)
    bkg_ref = f"BKG-FAIL-{uuid.uuid4().hex[:6].upper()}"
    try:
        # Insert booking on Trip 31, Seat 36
        cursor.execute("""
            INSERT INTO bookings (booking_reference, trip_id, passenger_id, seat_id, booking_time, booking_status, total_amount)
            VALUES (%s, 31, 1, 36, NOW(), 'CONFIRMED', 1200.00)
        """, (bkg_ref,))
        b_id = cursor.lastrowid

        # Simulate subsequent failure (duplicate transaction reference or invalid amount)
        cursor.execute("""
            INSERT INTO payments (booking_id, amount, payment_method, payment_status, payment_time, transaction_reference)
            VALUES (%s, -500.00, 'UPI', 'PAID', NOW(), 'TXN-FAIL-DUP')
        """, (b_id,))
    except Exception:
        # Issue rollback as app would
        db_conn.rollback()

    # Verify that booking was NOT committed to the database
    cursor.execute("SELECT * FROM bookings WHERE booking_reference = %s", (bkg_ref,))
    assert cursor.fetchone() is None
    cursor.close()

# -----------------------------------------------------------------------------
# 6. CANCELLATION TESTS
# -----------------------------------------------------------------------------
def test_successful_cancellation_and_trigger_sync(db_conn):
    """Test cancellation insertion and trigger trg_after_cancellation_sync state updates."""
    cursor = db_conn.cursor(dictionary=True)
    bkg_ref = f"BKG-CANCEL-TEST-{uuid.uuid4().hex[:4].upper()}"
    txn_ref = f"TXN-CANCEL-TEST-{uuid.uuid4().hex[:4].upper()}"
    try:
        # 1. Query an available seat dynamically
        cursor.execute("""
            SELECT s.seat_id 
            FROM seats s
            WHERE s.bus_id = (SELECT bus_id FROM trips WHERE trip_id = 31)
              AND s.seat_id NOT IN (
                  SELECT seat_id FROM bookings WHERE trip_id = 31 AND booking_status = 'CONFIRMED'
              )
            LIMIT 1
        """)
        free_seat = cursor.fetchone()
        assert free_seat is not None, "No free seat found on trip 31"
        s_id = free_seat['seat_id']

        # Create a booking on Trip 31, Seat s_id
        cursor.execute("""
            INSERT INTO bookings (booking_reference, trip_id, passenger_id, seat_id, booking_time, booking_status, total_amount)
            VALUES (%s, 31, 1, %s, NOW(), 'CONFIRMED', 1200.00)
        """, (bkg_ref, s_id))
        b_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO payments (booking_id, amount, payment_method, payment_status, payment_time, transaction_reference)
            VALUES (%s, 1200.00, 'UPI', 'PAID', NOW(), %s)
        """, (b_id, txn_ref))
        db_conn.commit()

        # 2. Insert Cancellation
        cursor.execute("""
            INSERT INTO cancellations (booking_id, cancellation_time, reason, refund_percentage, refund_amount)
            VALUES (%s, NOW(), 'Test cancellation reason', 100.00, 1200.00)
        """, (b_id,))
        c_id = cursor.lastrowid
        db_conn.commit()

        # 3. Verify trigger updated booking status to CANCELLED and payment to REFUNDED
        cursor.execute("SELECT booking_status FROM bookings WHERE booking_id = %s", (b_id,))
        assert cursor.fetchone()['booking_status'] == 'CANCELLED'

        cursor.execute("SELECT payment_status FROM payments WHERE booking_id = %s", (b_id,))
        assert cursor.fetchone()['payment_status'] == 'REFUNDED'

        # 4. Verify duplicate cancellation is rejected
        with pytest.raises(mysql.connector.Error) as exc_info:
            cursor.execute("""
                INSERT INTO cancellations (booking_id, cancellation_time, reason, refund_percentage, refund_amount)
                VALUES (%s, NOW(), 'Duplicate test', 100.00, 1200.00)
            """, (b_id,))
        db_conn.rollback()

        # Cleanup
        cursor.execute("DELETE FROM cancellations WHERE cancellation_id = %s", (c_id,))
        cursor.execute("DELETE FROM payments WHERE booking_id = %s", (b_id,))
        cursor.execute("DELETE FROM bookings WHERE booking_id = %s", (b_id,))
        db_conn.commit()
    finally:
        cursor.close()

# -----------------------------------------------------------------------------
# 7. DATABASE VIEWS ACCESSIBILITY TESTS
# -----------------------------------------------------------------------------
def test_database_views_accessibility(db_conn):
    """Test that all 7 database views execute without syntax or join errors."""
    cursor = db_conn.cursor(dictionary=True)
    views = [
        'available_trip_view',
        'trip_occupancy_view',
        'passenger_booking_history',
        'route_revenue_view',
        'fleet_utilization_view',
        'crew_schedule_view',
        'cancellation_report_view'
    ]
    for v in views:
        cursor.execute(f"SELECT * FROM {v} LIMIT 3")
        rows = cursor.fetchall()
        assert isinstance(rows, list)
    cursor.close()
