-- ============================================================================
-- BUS RESERVATION AND FLEET SCHEDULING SYSTEM
-- Relational Database Views (views.sql)
-- Target DBMS: MySQL 8.0+
-- Demonstrates multi-table joins, subqueries, group by, and aggregate functions
-- ============================================================================

USE bus_fleet_db;

-- ----------------------------------------------------------------------------
-- View 1: available_trip_view (v_available_trips)
-- Real-time seat inventory and tariff calculation for public booking.
-- Joins: trips, routes, buses, fares, and correlated count of confirmed bookings.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW available_trip_view AS
SELECT 
    t.trip_id,
    r.route_id,
    r.route_name,
    r.source,
    r.destination,
    r.distance_km,
    b.bus_id,
    b.bus_number,
    b.bus_type,
    b.total_seats,
    COALESCE(booked_data.booked_seats, 0) AS booked_seats,
    (b.total_seats - COALESCE(booked_data.booked_seats, 0)) AS available_seats,
    COALESCE(f.amount, 0.00) AS fare,
    t.departure_time,
    t.arrival_time,
    t.trip_status
FROM trips t
INNER JOIN routes r ON t.route_id = r.route_id
INNER JOIN buses b ON t.bus_id = b.bus_id
LEFT JOIN fares f ON t.trip_id = f.trip_id
LEFT JOIN (
    SELECT trip_id, COUNT(*) AS booked_seats
    FROM bookings
    WHERE booking_status = 'CONFIRMED'
    GROUP BY trip_id
) booked_data ON t.trip_id = booked_data.trip_id
WHERE t.trip_status IN ('PUBLISHED', 'SCHEDULED');

-- ----------------------------------------------------------------------------
-- View 2: trip_occupancy_view (v_trip_occupancy)
-- Analytical view showing operational efficiency and load factors of trips.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW trip_occupancy_view AS
SELECT 
    t.trip_id,
    r.route_name,
    r.source,
    r.destination,
    b.bus_number,
    b.bus_type,
    t.departure_time,
    t.arrival_time,
    t.trip_status,
    b.total_seats,
    COUNT(CASE WHEN bk.booking_status = 'CONFIRMED' THEN bk.booking_id END) AS booked_seats,
    COUNT(CASE WHEN bk.booking_status = 'CANCELLED' THEN bk.booking_id END) AS cancelled_bookings,
    ROUND(
        (COUNT(CASE WHEN bk.booking_status = 'CONFIRMED' THEN bk.booking_id END) / b.total_seats) * 100.0, 
        2
    ) AS occupancy_percentage
FROM trips t
INNER JOIN routes r ON t.route_id = r.route_id
INNER JOIN buses b ON t.bus_id = b.bus_id
LEFT JOIN bookings bk ON t.trip_id = bk.trip_id
GROUP BY t.trip_id, r.route_name, r.source, r.destination, b.bus_number, b.bus_type, t.departure_time, t.arrival_time, t.trip_status, b.total_seats;

-- ----------------------------------------------------------------------------
-- View 3: passenger_booking_history (v_passenger_booking_history)
-- Comprehensive passenger audit trail linking tickets, seats, trips, and payments.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW passenger_booking_history AS
SELECT 
    p.passenger_id,
    p.name AS passenger_name,
    p.phone AS passenger_phone,
    p.email AS passenger_email,
    bk.booking_id,
    bk.booking_reference,
    bk.booking_time,
    bk.booking_status,
    s.seat_number,
    s.seat_type,
    s.deck,
    t.trip_id,
    r.route_name,
    r.source,
    r.destination,
    t.departure_time,
    t.arrival_time,
    b.bus_number,
    b.bus_type,
    bk.total_amount,
    COALESCE(pm.payment_method, 'N/A') AS payment_method,
    COALESCE(pm.payment_status, 'PENDING') AS payment_status,
    pm.transaction_reference,
    c.cancellation_time,
    c.refund_amount
FROM passengers p
INNER JOIN bookings bk ON p.passenger_id = bk.passenger_id
INNER JOIN seats s ON bk.seat_id = s.seat_id
INNER JOIN trips t ON bk.trip_id = t.trip_id
INNER JOIN routes r ON t.route_id = r.route_id
INNER JOIN buses b ON t.bus_id = b.bus_id
LEFT JOIN payments pm ON bk.booking_id = pm.booking_id
LEFT JOIN cancellations c ON bk.booking_id = c.booking_id;

-- ----------------------------------------------------------------------------
-- View 4: route_revenue_view (v_route_revenue)
-- Financial report view calculating total net revenue generated per route.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW route_revenue_view AS
SELECT 
    r.route_id,
    r.route_name,
    r.source,
    r.destination,
    r.distance_km,
    COUNT(DISTINCT t.trip_id) AS total_trips,
    COUNT(DISTINCT CASE WHEN bk.booking_status = 'CONFIRMED' THEN bk.booking_id END) AS confirmed_bookings,
    COUNT(DISTINCT c.cancellation_id) AS cancelled_bookings,
    COALESCE(SUM(CASE WHEN bk.booking_status = 'CONFIRMED' THEN bk.total_amount ELSE 0 END), 0.00) AS gross_revenue,
    COALESCE(SUM(c.refund_amount), 0.00) AS total_refunds,
    (
        COALESCE(SUM(CASE WHEN bk.booking_status = 'CONFIRMED' THEN bk.total_amount ELSE 0 END), 0.00) -
        COALESCE(SUM(c.refund_amount), 0.00)
    ) AS net_revenue
FROM routes r
LEFT JOIN trips t ON r.route_id = t.route_id
LEFT JOIN bookings bk ON t.trip_id = bk.trip_id
LEFT JOIN cancellations c ON bk.booking_id = c.booking_id
GROUP BY r.route_id, r.route_name, r.source, r.destination, r.distance_km;

-- ----------------------------------------------------------------------------
-- View 5: fleet_utilization_view
-- Fleet analytics assessing bus asset utilization and yield.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW fleet_utilization_view AS
SELECT 
    b.bus_id,
    b.registration_number,
    b.bus_number,
    b.bus_type,
    b.total_seats,
    b.status AS bus_status,
    COUNT(DISTINCT t.trip_id) AS total_trips_assigned,
    COUNT(DISTINCT CASE WHEN t.trip_status = 'COMPLETED' THEN t.trip_id END) AS completed_trips,
    COUNT(DISTINCT CASE WHEN bk.booking_status = 'CONFIRMED' THEN bk.booking_id END) AS total_passengers_carried,
    COALESCE(SUM(CASE WHEN bk.booking_status = 'CONFIRMED' THEN bk.total_amount ELSE 0 END), 0.00) AS total_revenue_generated
FROM buses b
LEFT JOIN trips t ON b.bus_id = t.bus_id
LEFT JOIN bookings bk ON t.trip_id = bk.trip_id
GROUP BY b.bus_id, b.registration_number, b.bus_number, b.bus_type, b.total_seats, b.status;

-- ----------------------------------------------------------------------------
-- View 6: crew_schedule_view
-- Operational dispatch view coordinating drivers and conductors across trips.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW crew_schedule_view AS
SELECT 
    ca.assignment_id,
    t.trip_id,
    t.trip_status,
    r.route_name,
    r.source,
    r.destination,
    t.departure_time,
    t.arrival_time,
    d.driver_id,
    d.name AS driver_name,
    d.phone AS driver_phone,
    d.license_number,
    c.conductor_id,
    c.name AS conductor_name,
    c.phone AS conductor_phone,
    c.employee_code,
    b.bus_number
FROM crew_assignments ca
INNER JOIN trips t ON ca.trip_id = t.trip_id
INNER JOIN routes r ON t.route_id = r.route_id
INNER JOIN buses b ON t.bus_id = b.bus_id
INNER JOIN drivers d ON ca.driver_id = d.driver_id
INNER JOIN conductors c ON ca.conductor_id = c.conductor_id;

-- ----------------------------------------------------------------------------
-- View 7: cancellation_report_view
-- Audit view analyzing refunds and cancellation drivers.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW cancellation_report_view AS
SELECT 
    c.cancellation_id,
    c.cancellation_time,
    bk.booking_reference,
    p.name AS passenger_name,
    p.phone AS passenger_phone,
    r.route_name,
    t.departure_time,
    bk.total_amount AS original_fare,
    c.refund_percentage,
    c.refund_amount,
    c.reason
FROM cancellations c
INNER JOIN bookings bk ON c.booking_id = bk.booking_id
INNER JOIN passengers p ON bk.passenger_id = p.passenger_id
INNER JOIN trips t ON bk.trip_id = t.trip_id
INNER JOIN routes r ON t.route_id = r.route_id;
