-- ============================================================================
-- BUS RESERVATION AND FLEET SCHEDULING SYSTEM
-- Database Schema Definition (schema.sql)
-- Target DBMS: MySQL 8.0+
-- Normalization Standard: Third Normal Form (3NF)
-- ============================================================================

CREATE DATABASE IF NOT EXISTS bus_fleet_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE bus_fleet_db;

-- Drop dependent tables in reverse dependency order for clean recreation
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS cancellations;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS fares;
DROP TABLE IF EXISTS crew_assignments;
DROP TABLE IF EXISTS trips;
DROP TABLE IF EXISTS seats;
DROP TABLE IF EXISTS route_stops;
DROP TABLE IF EXISTS stops;
DROP TABLE IF EXISTS routes;
DROP TABLE IF EXISTS conductors;
DROP TABLE IF EXISTS drivers;
DROP TABLE IF EXISTS buses;
DROP TABLE IF EXISTS passengers;
DROP TABLE IF EXISTS admin_users;

-- ----------------------------------------------------------------------------
-- 1. Table: BUSES
-- Represents the fleet assets owned or operated by the transport agency.
-- Normalized to 3NF: bus_id is the primary key; attributes depend only on PK.
-- ----------------------------------------------------------------------------
CREATE TABLE buses (
    bus_id INT AUTO_INCREMENT PRIMARY KEY,
    registration_number VARCHAR(20) NOT NULL UNIQUE,
    bus_number VARCHAR(20) NOT NULL UNIQUE,
    bus_type ENUM('AC Sleeper', 'Non-AC Seater', 'Volvo Multi-Axle', 'AC Seater', 'Electric AC') NOT NULL,
    total_seats INT NOT NULL,
    status ENUM('ACTIVE', 'MAINTENANCE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_total_seats CHECK (total_seats > 0 AND total_seats <= 60)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 2. Table: ROUTES
-- Represents arterial travel paths connecting origin and destination hubs.
-- ----------------------------------------------------------------------------
CREATE TABLE routes (
    route_id INT AUTO_INCREMENT PRIMARY KEY,
    route_name VARCHAR(100) NOT NULL UNIQUE,
    source VARCHAR(60) NOT NULL,
    destination VARCHAR(60) NOT NULL,
    distance_km DECIMAL(6,2) NOT NULL,
    estimated_duration_hours DECIMAL(4,2) NOT NULL DEFAULT 8.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_route_distance CHECK (distance_km > 0),
    CONSTRAINT chk_route_src_dst CHECK (source != destination)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 3. Table: STOPS
-- Master table of designated passenger boarding and dropping points.
-- ----------------------------------------------------------------------------
CREATE TABLE stops (
    stop_id INT AUTO_INCREMENT PRIMARY KEY,
    stop_name VARCHAR(100) NOT NULL,
    city VARCHAR(60) NOT NULL,
    location_landmark VARCHAR(150),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_stop_name_city UNIQUE (stop_name, city)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 4. Table: ROUTE_STOPS (Resolves M:N relationship between ROUTES and STOPS)
-- Defines intermediate waypoints, chronological ordering, and arrival offsets.
-- ----------------------------------------------------------------------------
CREATE TABLE route_stops (
    route_id INT NOT NULL,
    stop_id INT NOT NULL,
    stop_order INT NOT NULL,
    arrival_offset_mins INT NOT NULL DEFAULT 0,
    departure_offset_mins INT NOT NULL DEFAULT 0,
    PRIMARY KEY (route_id, stop_order),
    CONSTRAINT uq_route_stop UNIQUE (route_id, stop_id),
    CONSTRAINT fk_rs_route FOREIGN KEY (route_id) REFERENCES routes(route_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_rs_stop FOREIGN KEY (stop_id) REFERENCES stops(stop_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_stop_order CHECK (stop_order >= 1),
    CONSTRAINT chk_offset_order CHECK (departure_offset_mins >= arrival_offset_mins)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 5. Table: SEATS
-- Physical inventory of seats belonging to each specific bus.
-- Ensures Rule 3: A bus cannot have duplicate seat numbers.
-- ----------------------------------------------------------------------------
CREATE TABLE seats (
    seat_id INT AUTO_INCREMENT PRIMARY KEY,
    bus_id INT NOT NULL,
    seat_number VARCHAR(10) NOT NULL,
    seat_type ENUM('WINDOW', 'AISLE', 'SLEEPER_LOWER', 'SLEEPER_UPPER', 'SINGLE') NOT NULL DEFAULT 'AISLE',
    deck ENUM('LOWER', 'UPPER') NOT NULL DEFAULT 'LOWER',
    CONSTRAINT uq_bus_seat UNIQUE (bus_id, seat_number),
    CONSTRAINT fk_seats_bus FOREIGN KEY (bus_id) REFERENCES buses(bus_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 6. Table: DRIVERS
-- Certified operational personnel licensed to operate heavy passenger motor vehicles.
-- ----------------------------------------------------------------------------
CREATE TABLE drivers (
    driver_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL UNIQUE,
    license_number VARCHAR(40) NOT NULL UNIQUE,
    experience_years INT NOT NULL DEFAULT 1,
    status ENUM('ACTIVE', 'ON_LEAVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_driver_exp CHECK (experience_years >= 0)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 7. Table: CONDUCTORS
-- Operational personnel managing boarding, tickets, passenger care, and safety.
-- ----------------------------------------------------------------------------
CREATE TABLE conductors (
    conductor_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL UNIQUE,
    employee_code VARCHAR(30) NOT NULL UNIQUE,
    status ENUM('ACTIVE', 'ON_LEAVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 8. Table: TRIPS
-- Core operational entity representing a planned journey of a bus on a route.
-- Enforces Rule 4: Departure time must precede arrival time.
-- ----------------------------------------------------------------------------
CREATE TABLE trips (
    trip_id INT AUTO_INCREMENT PRIMARY KEY,
    bus_id INT NOT NULL,
    route_id INT NOT NULL,
    departure_time DATETIME NOT NULL,
    arrival_time DATETIME NOT NULL,
    trip_status ENUM('SCHEDULED', 'PUBLISHED', 'COMPLETED', 'CANCELLED') NOT NULL DEFAULT 'SCHEDULED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_trips_bus FOREIGN KEY (bus_id) REFERENCES buses(bus_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_trips_route FOREIGN KEY (route_id) REFERENCES routes(route_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_trip_schedule CHECK (departure_time < arrival_time)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 9. Table: CREW_ASSIGNMENTS
-- Links a driver and conductor to a trip schedule.
-- ----------------------------------------------------------------------------
CREATE TABLE crew_assignments (
    assignment_id INT AUTO_INCREMENT PRIMARY KEY,
    trip_id INT NOT NULL UNIQUE,
    driver_id INT NOT NULL,
    conductor_id INT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ca_trip FOREIGN KEY (trip_id) REFERENCES trips(trip_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_ca_driver FOREIGN KEY (driver_id) REFERENCES drivers(driver_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_ca_conductor FOREIGN KEY (conductor_id) REFERENCES conductors(conductor_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 10. Table: FARES
-- Tariff specification associated with a trip.
-- ----------------------------------------------------------------------------
CREATE TABLE fares (
    fare_id INT AUTO_INCREMENT PRIMARY KEY,
    trip_id INT NOT NULL UNIQUE,
    amount DECIMAL(8,2) NOT NULL,
    currency VARCHAR(5) NOT NULL DEFAULT 'INR',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_fares_trip FOREIGN KEY (trip_id) REFERENCES trips(trip_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_fare_amount CHECK (amount > 0)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 11. Table: PASSENGERS
-- Customer entity containing identifiable passenger profile data.
-- ----------------------------------------------------------------------------
CREATE TABLE passengers (
    passenger_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    gender ENUM('MALE', 'FEMALE', 'OTHER') NOT NULL DEFAULT 'MALE',
    age INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_passenger_age CHECK (age >= 1 AND age <= 120)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 12. Table: BOOKINGS
-- Reservation ledger recording passenger seat purchases on specific trips.
-- ----------------------------------------------------------------------------
CREATE TABLE bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_reference VARCHAR(25) NOT NULL UNIQUE,
    trip_id INT NOT NULL,
    passenger_id INT NOT NULL,
    seat_id INT NOT NULL,
    booking_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    booking_status ENUM('CONFIRMED', 'CANCELLED') NOT NULL DEFAULT 'CONFIRMED',
    total_amount DECIMAL(8,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_bookings_trip FOREIGN KEY (trip_id) REFERENCES trips(trip_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_bookings_passenger FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_bookings_seat FOREIGN KEY (seat_id) REFERENCES seats(seat_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_booking_amount CHECK (total_amount >= 0)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 13. Table: CANCELLATIONS
-- Audit record for booking revocations and computed refund disbursements.
-- Enforces Rule 9: A booking can only be cancelled once (booking_id is UNIQUE).
-- ----------------------------------------------------------------------------
CREATE TABLE cancellations (
    cancellation_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL UNIQUE,
    cancellation_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason VARCHAR(255) NOT NULL,
    refund_percentage DECIMAL(5,2) NOT NULL,
    refund_amount DECIMAL(8,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cancellations_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_refund_pct CHECK (refund_percentage >= 0 AND refund_percentage <= 100),
    CONSTRAINT chk_refund_amt CHECK (refund_amount >= 0)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 14. Table: PAYMENTS
-- Transaction settlement log linked 1:1 with bookings.
-- ----------------------------------------------------------------------------
CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL UNIQUE,
    amount DECIMAL(8,2) NOT NULL,
    payment_method ENUM('UPI', 'CREDIT_CARD', 'DEBIT_CARD', 'NET_BANKING', 'CASH') NOT NULL,
    payment_status ENUM('PENDING', 'PAID', 'REFUNDED', 'FAILED') NOT NULL DEFAULT 'PAID',
    payment_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    transaction_reference VARCHAR(60) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_payments_booking FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_payment_amount CHECK (amount > 0)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- 15. Table: ADMIN_USERS
-- System authentication table for operator and administrative access.
-- ----------------------------------------------------------------------------
CREATE TABLE admin_users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role ENUM('ADMIN', 'OPERATOR', 'DISPATCHER') NOT NULL DEFAULT 'ADMIN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
