-- ============================================================================
-- BUS RESERVATION AND FLEET SCHEDULING SYSTEM
-- SQL Concept Demonstration Repository (queries.sql)
-- DBMS Academic Viva Demonstration Script
-- Target DBMS: MySQL 8.0+
-- ============================================================================

USE bus_fleet_db;

-- ----------------------------------------------------------------------------
-- 1. INSERT DEMONSTRATION
-- Concept: Adding new entity records with foreign keys and constraints
-- ----------------------------------------------------------------------------
-- Insert a new passenger record into the PASSENGERS table
INSERT INTO passengers (name, phone, email, gender, age)
VALUES ('Kavitha Krishnan', '9876543299', 'kavitha.krishnan@example.com', 'FEMALE', 28);

-- ----------------------------------------------------------------------------
-- 2. UPDATE DEMONSTRATION
-- Concept: Modifying existing row attributes based on conditional predicates
-- ----------------------------------------------------------------------------
-- Update driver status to 'ON_LEAVE' for driver_id = 3
UPDATE drivers
SET status = 'ON_LEAVE'
WHERE driver_id = 3;

-- ----------------------------------------------------------------------------
-- 3. DELETE DEMONSTRATION
-- Concept: Removing stale or test records with referential integrity adherence
-- ----------------------------------------------------------------------------
-- Delete inactive passengers who have zero bookings
DELETE FROM passengers
WHERE passenger_id NOT IN (SELECT DISTINCT passenger_id FROM bookings)
  AND email LIKE '%test%';

-- ----------------------------------------------------------------------------
-- 4. BASIC SELECT WITH WHERE AND ORDER BY
-- Concept: Projection, filtering using relational operators, and sorting
-- ----------------------------------------------------------------------------
-- List all active buses sorted by total seat capacity in descending order
SELECT bus_id, registration_number, bus_number, bus_type, total_seats, status
FROM buses
WHERE status = 'ACTIVE'
ORDER BY total_seats DESC, bus_number ASC;

-- ----------------------------------------------------------------------------
-- 5. GROUP BY WITH AGGREGATE FUNCTIONS (COUNT, SUM, AVG, MIN, MAX)
-- Concept: Aggregation over partitions of relations
-- ----------------------------------------------------------------------------
-- Aggregate fleet metrics categorized by bus type
SELECT 
    bus_type,
    COUNT(*) AS total_buses,
    SUM(total_seats) AS fleet_capacity,
    ROUND(AVG(total_seats), 1) AS avg_capacity_per_bus,
    MIN(total_seats) AS min_seats,
    MAX(total_seats) AS max_seats
FROM buses
GROUP BY bus_type
ORDER BY total_buses DESC;

-- ----------------------------------------------------------------------------
-- 6. HAVING CLAUSE
-- Concept: Filtering grouped partitions after aggregation
-- ----------------------------------------------------------------------------
-- Find routes that have scheduled at least 3 trips with total confirmed booking count > 5
SELECT 
    r.route_id,
    r.route_name,
    COUNT(DISTINCT t.trip_id) AS total_trips,
    COUNT(bk.booking_id) AS confirmed_bookings
FROM routes r
INNER JOIN trips t ON r.route_id = t.route_id
LEFT JOIN bookings bk ON t.trip_id = bk.trip_id AND bk.booking_status = 'CONFIRMED'
GROUP BY r.route_id, r.route_name
HAVING COUNT(DISTINCT t.trip_id) >= 2 AND COUNT(bk.booking_id) > 2
ORDER BY confirmed_bookings DESC;

-- ----------------------------------------------------------------------------
-- 7. INNER JOIN (2-TABLE & 3-TABLE)
-- Concept: Relational equi-join matching tuples across relations
-- ----------------------------------------------------------------------------
-- List trips with their assigned route and bus specifications
SELECT 
    t.trip_id,
    r.route_name,
    r.source,
    r.destination,
    b.bus_number,
    b.bus_type,
    t.departure_time,
    t.arrival_time,
    t.trip_status
FROM trips t
INNER JOIN routes r ON t.route_id = r.route_id
INNER JOIN buses b ON t.bus_id = b.bus_id
WHERE t.trip_status = 'PUBLISHED'
ORDER BY t.departure_time ASC;

-- ----------------------------------------------------------------------------
-- 8. LEFT OUTER JOIN
-- Concept: Preserving all tuples from the left relation regardless of match
-- ----------------------------------------------------------------------------
-- Find all drivers and their assigned trips (including idle drivers with no trips)
SELECT 
    d.driver_id,
    d.name AS driver_name,
    d.phone,
    d.status AS driver_status,
    t.trip_id,
    r.route_name,
    t.departure_time
FROM drivers d
LEFT JOIN crew_assignments ca ON d.driver_id = ca.driver_id
LEFT JOIN trips t ON ca.trip_id = t.trip_id
LEFT JOIN routes r ON t.route_id = r.route_id
ORDER BY d.driver_id, t.departure_time;

-- ----------------------------------------------------------------------------
-- 9. MULTIPLE-TABLE COMPLEX JOIN (7 TABLES)
-- Concept: Comprehensive relational traversal across enterprise entities
-- ----------------------------------------------------------------------------
-- Full ticket dossier linking Booking -> Passenger -> Trip -> Route -> Bus -> Seat -> Payment
SELECT 
    bk.booking_reference,
    p.name AS passenger_name,
    p.phone AS passenger_phone,
    r.route_name,
    b.bus_number,
    s.seat_number,
    s.seat_type,
    t.departure_time,
    bk.total_amount,
    pm.payment_method,
    pm.payment_status,
    pm.transaction_reference
FROM bookings bk
INNER JOIN passengers p ON bk.passenger_id = p.passenger_id
INNER JOIN trips t ON bk.trip_id = t.trip_id
INNER JOIN routes r ON t.route_id = r.route_id
INNER JOIN buses b ON t.bus_id = b.bus_id
INNER JOIN seats s ON bk.seat_id = s.seat_id
INNER JOIN payments pm ON bk.booking_id = pm.booking_id
WHERE bk.booking_status = 'CONFIRMED'
ORDER BY bk.booking_time DESC
LIMIT 10;

-- ----------------------------------------------------------------------------
-- 10. SUBQUERY IN WHERE CLAUSE (SCALAR SUBQUERY)
-- Concept: Comparing tuple values against scalar aggregated subquery results
-- ----------------------------------------------------------------------------
-- Find routes whose travel distance is greater than the fleet average route distance
SELECT 
    route_id,
    route_name,
    source,
    destination,
    distance_km
FROM routes
WHERE distance_km > (
    SELECT AVG(distance_km) 
    FROM routes
)
ORDER BY distance_km DESC;

-- ----------------------------------------------------------------------------
-- 11. NESTED CORRELATED SUBQUERY
-- Concept: Inner query references outer query attributes evaluated row-by-row
-- ----------------------------------------------------------------------------
-- Find trips that have above-average booking counts compared to other trips on the same route
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
);

-- ----------------------------------------------------------------------------
-- 12. EXISTS & NOT EXISTS DEMONSTRATION
-- Concept: Semi-join and anti-semi-join existential qualification
-- ----------------------------------------------------------------------------
-- A) Find trips that have at least one cancellation record (EXISTS)
SELECT 
    t.trip_id,
    r.route_name,
    t.departure_time
FROM trips t
JOIN routes r ON t.route_id = r.route_id
WHERE EXISTS (
    SELECT 1 
    FROM bookings bk 
    JOIN cancellations c ON bk.booking_id = c.booking_id
    WHERE bk.trip_id = t.trip_id
);

-- B) Find active drivers who currently have NO assigned upcoming trips (NOT EXISTS)
SELECT 
    d.driver_id,
    d.name,
    d.phone,
    d.license_number
FROM drivers d
WHERE d.status = 'ACTIVE'
  AND NOT EXISTS (
      SELECT 1 
      FROM crew_assignments ca
      JOIN trips t ON ca.trip_id = t.trip_id
      WHERE ca.driver_id = d.driver_id
        AND t.trip_status IN ('SCHEDULED', 'PUBLISHED')
  );

-- ----------------------------------------------------------------------------
-- 13. BETWEEN OPERATOR
-- Concept: Inclusive range query on continuous or temporal domains
-- ----------------------------------------------------------------------------
-- Select trips departing between a specific travel window
SELECT 
    t.trip_id,
    r.route_name,
    t.departure_time,
    t.arrival_time,
    f.amount AS fare
FROM trips t
JOIN routes r ON t.route_id = r.route_id
LEFT JOIN fares f ON t.trip_id = f.trip_id
WHERE t.departure_time BETWEEN '2026-10-01 00:00:00' AND '2026-10-31 23:59:59'
ORDER BY t.departure_time ASC;

-- ----------------------------------------------------------------------------
-- 14. LIKE OPERATOR WITH WILDCARDS
-- Concept: String pattern matching using '%' and '_'
-- ----------------------------------------------------------------------------
-- Find all passengers with Gmail addresses or phone numbers starting with '98'
SELECT passenger_id, name, phone, email
FROM passengers
WHERE email LIKE '%@gmail.com' AND phone LIKE '98%'
ORDER BY name ASC;

-- ----------------------------------------------------------------------------
-- 15. CASE CONDITIONAL EXPRESSION
-- Concept: Categorical projection based on multi-branch condition evaluation
-- ----------------------------------------------------------------------------
-- Classify trips into Occupancy Tiers based on booked seat ratio
SELECT 
    t.trip_id,
    r.route_name,
    b.bus_number,
    b.total_seats,
    COUNT(CASE WHEN bk.booking_status = 'CONFIRMED' THEN bk.booking_id END) AS confirmed_seats,
    ROUND(COUNT(CASE WHEN bk.booking_status = 'CONFIRMED' THEN bk.booking_id END) * 100.0 / b.total_seats, 1) AS occupancy_pct,
    CASE 
        WHEN (COUNT(CASE WHEN bk.booking_status = 'CONFIRMED' THEN bk.booking_id END) * 1.0 / b.total_seats) >= 0.80 THEN 'High Demand (>=80%)'
        WHEN (COUNT(CASE WHEN bk.booking_status = 'CONFIRMED' THEN bk.booking_id END) * 1.0 / b.total_seats) >= 0.40 THEN 'Moderate Demand (40-79%)'
        ELSE 'Low Occupancy (<40%)'
    END AS occupancy_category
FROM trips t
JOIN routes r ON t.route_id = r.route_id
JOIN buses b ON t.bus_id = b.bus_id
LEFT JOIN bookings bk ON t.trip_id = bk.trip_id
GROUP BY t.trip_id, r.route_name, b.bus_number, b.total_seats
ORDER BY occupancy_pct DESC;

-- ----------------------------------------------------------------------------
-- 16. QUERYING DATABASE VIEWS
-- Concept: Abstracting complex join logic through schema views
-- ----------------------------------------------------------------------------
-- Query the top revenue producing routes from the route_revenue_view
SELECT route_name, source, destination, total_trips, confirmed_bookings, gross_revenue, net_revenue
FROM route_revenue_view
ORDER BY net_revenue DESC;

-- ----------------------------------------------------------------------------
-- 17. TRANSACTION DEMONSTRATION (ACID COMPLIANCE)
-- Concept: Atomic seat reservation with commit or rollback
-- ----------------------------------------------------------------------------
START TRANSACTION;

-- Step 1: Verify and lock candidate trip and seat
SELECT t.trip_id, t.bus_id, f.amount
FROM trips t
JOIN fares f ON t.trip_id = f.trip_id
WHERE t.trip_id = 1 AND t.trip_status = 'PUBLISHED'
FOR UPDATE;

-- Step 2: Ensure seat is not already confirmed
-- (If count > 0, application issues ROLLBACK)
SELECT COUNT(*) INTO @existing_cnt
FROM bookings
WHERE trip_id = 1 AND seat_id = 5 AND booking_status = 'CONFIRMED';

-- Step 3: Insert booking
INSERT INTO bookings (booking_reference, trip_id, passenger_id, seat_id, booking_time, booking_status, total_amount)
VALUES ('BKG-DEMO-9999', 1, 1, 5, NOW(), 'CONFIRMED', 850.00);

SET @new_booking_id = LAST_INSERT_ID();

-- Step 4: Insert corresponding payment
INSERT INTO payments (booking_id, amount, payment_method, payment_status, payment_time, transaction_reference)
VALUES (@new_booking_id, 850.00, 'UPI', 'PAID', NOW(), 'TXN-DEMO-9999');

-- Commit transaction atomically
COMMIT;
