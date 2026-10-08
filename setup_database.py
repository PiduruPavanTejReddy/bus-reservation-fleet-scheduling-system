"""Database initialization script for Bus Reservation and Fleet Scheduling System."""
import subprocess
import sys
import mysql.connector
from config import Config

def init_db():
    print("=" * 70)
    print("BUS RESERVATION AND FLEET SCHEDULING SYSTEM - DATABASE SETUP")
    print("=" * 70)
    print(f"Connecting to MySQL Host: {Config.MYSQL_HOST}:{Config.MYSQL_PORT}")
    print(f"Target Database: {Config.MYSQL_DB}")
    print(f"User: {Config.MYSQL_USER}")

    # Step 1: Create Database if not exists
    try:
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.MYSQL_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.commit()
        cursor.close()
        conn.close()
        print("Database confirmed/created.")
    except Exception as e:
        print(f"Database connection error: {e}")
        sys.exit(1)

    # Step 2: Execute SQL files via mysql CLI for proper DELIMITER and script parsing
    files = [
        'database/schema.sql',
        'database/constraints.sql',
        'database/views.sql',
        'database/seed_data.sql'
    ]

    for sql_file in files:
        print(f"Executing {sql_file}...")
        cmd = [
            'mysql',
            f"-h{Config.MYSQL_HOST}",
            f"-P{Config.MYSQL_PORT}",
            f"-u{Config.MYSQL_USER}",
            f"-p{Config.MYSQL_PASSWORD}",
            Config.MYSQL_DB
        ]
        with open(sql_file, 'r', encoding='utf-8') as f:
            content = f.read()

        res = subprocess.run(cmd, input=content, text=True, capture_output=True)
        if res.returncode != 0:
            print(f"Error executing {sql_file}:")
            print(res.stderr)
            sys.exit(1)
        else:
            print(f"  -> Successfully applied {sql_file}")

    # Step 3: Verification
    print("\n" + "=" * 70)
    print("DATABASE VERIFICATION SUMMARY")
    print("=" * 70)
    conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB
    )
    cursor = conn.cursor()
    tables = [
        'buses', 'routes', 'stops', 'route_stops', 'seats',
        'drivers', 'conductors', 'trips', 'crew_assignments',
        'fares', 'passengers', 'bookings', 'cancellations',
        'payments', 'admin_users'
    ]
    for tbl in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {tbl};")
        cnt = cursor.fetchone()[0]
        print(f"  Table: {tbl.ljust(22)} Rows: {str(cnt).rjust(4)}")

    views = [
        'available_trip_view', 'trip_occupancy_view', 'passenger_booking_history',
        'route_revenue_view', 'fleet_utilization_view', 'crew_schedule_view',
        'cancellation_report_view'
    ]
    print("\nDatabase Views:")
    for v in views:
        cursor.execute(f"SELECT COUNT(*) FROM {v};")
        cnt = cursor.fetchone()[0]
        print(f"  View:  {v.ljust(26)} Accessible Rows: {str(cnt).rjust(4)}")

    cursor.close()
    conn.close()
    print("\nSetup successfully completed! Database is fully initialized.")

if __name__ == '__main__':
    init_db()
