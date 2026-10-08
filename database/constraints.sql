-- ============================================================================
-- BUS RESERVATION AND FLEET SCHEDULING SYSTEM
-- Advanced Constraints, Indexes, and Integrity Triggers (constraints.sql)
-- Target DBMS: MySQL 8.0+
-- ============================================================================

USE bus_fleet_db;

-- ----------------------------------------------------------------------------
-- PERFORMANCE INDEXES
-- Indexing frequently queried search criteria, join keys, and foreign keys.
-- ----------------------------------------------------------------------------
CREATE INDEX idx_passenger_phone ON passengers(phone);
CREATE INDEX idx_passenger_email ON passengers(email);
CREATE INDEX idx_passenger_name ON passengers(name);

CREATE INDEX idx_trip_departure ON trips(departure_time);
CREATE INDEX idx_trip_arrival ON trips(arrival_time);
CREATE INDEX idx_trip_route ON trips(route_id);
CREATE INDEX idx_trip_bus ON trips(bus_id);
CREATE INDEX idx_trip_status ON trips(trip_status);

CREATE INDEX idx_booking_trip ON bookings(trip_id);
CREATE INDEX idx_booking_passenger ON bookings(passenger_id);
CREATE INDEX idx_booking_seat ON bookings(seat_id);
CREATE INDEX idx_booking_status ON bookings(booking_status);
CREATE INDEX idx_booking_time ON bookings(booking_time);

CREATE INDEX idx_payment_status ON payments(payment_status);
CREATE INDEX idx_payment_method ON payments(payment_method);
CREATE INDEX idx_payment_time ON payments(payment_time);

CREATE INDEX idx_bus_reg ON buses(registration_number);
CREATE INDEX idx_bus_status ON buses(status);

CREATE INDEX idx_route_endpoints ON routes(source, destination);

-- ----------------------------------------------------------------------------
-- BUSINESS RULE TRIGGERS
-- Enforces declarative business logic and ACID consistency at the database level.
-- ----------------------------------------------------------------------------

DELIMITER $$

-- ----------------------------------------------------------------------------
-- Trigger 1: Prevent Duplicate Active Booking for Same Seat on Same Trip
-- Rule 1: A passenger cannot book the same seat twice for the same trip.
-- Cancelled bookings free up the seat for new reservations.
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_prevent_duplicate_seat_booking$$
CREATE TRIGGER trg_prevent_duplicate_seat_booking
BEFORE INSERT ON bookings
FOR EACH ROW
BEGIN
    DECLARE v_active_count INT DEFAULT 0;
    
    SELECT COUNT(*) INTO v_active_count
    FROM bookings
    WHERE trip_id = NEW.trip_id
      AND seat_id = NEW.seat_id
      AND booking_status = 'CONFIRMED';
      
    IF v_active_count > 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Seat is already booked for this trip.';
    END IF;
END$$

-- ----------------------------------------------------------------------------
-- Trigger 2: Prevent Duplicate Active Booking upon Update
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_prevent_duplicate_seat_booking_update$$
CREATE TRIGGER trg_prevent_duplicate_seat_booking_update
BEFORE UPDATE ON bookings
FOR EACH ROW
BEGIN
    DECLARE v_active_count INT DEFAULT 0;
    
    IF NEW.booking_status = 'CONFIRMED' AND (OLD.booking_status != 'CONFIRMED' OR OLD.seat_id != NEW.seat_id OR OLD.trip_id != NEW.trip_id) THEN
        SELECT COUNT(*) INTO v_active_count
        FROM bookings
        WHERE trip_id = NEW.trip_id
          AND seat_id = NEW.seat_id
          AND booking_id != NEW.booking_id
          AND booking_status = 'CONFIRMED';
          
        IF v_active_count > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Seat is already booked for this trip.';
        END IF;
    END IF;
END$$

-- ----------------------------------------------------------------------------
-- Trigger 3: Validate Seat Belongs to Bus Assigned to the Trip
-- Rule 2: A seat must belong to the bus assigned to that trip.
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_validate_seat_belongs_to_bus$$
CREATE TRIGGER trg_validate_seat_belongs_to_bus
BEFORE INSERT ON bookings
FOR EACH ROW
BEGIN
    DECLARE v_trip_bus_id INT;
    DECLARE v_seat_bus_id INT;
    
    SELECT bus_id INTO v_trip_bus_id FROM trips WHERE trip_id = NEW.trip_id;
    SELECT bus_id INTO v_seat_bus_id FROM seats WHERE seat_id = NEW.seat_id;
    
    IF v_trip_bus_id IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trip does not exist.';
    END IF;
    
    IF v_seat_bus_id IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Seat does not exist.';
    END IF;
    
    IF v_trip_bus_id != v_seat_bus_id THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Seat does not belong to the bus assigned to this trip.';
    END IF;
END$$

-- ----------------------------------------------------------------------------
-- Trigger 4: Prevent Bus Assignment to Overlapping Trips
-- Rule 5: A bus cannot operate two concurrent trips.
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_prevent_bus_overlap$$
CREATE TRIGGER trg_prevent_bus_overlap
BEFORE INSERT ON trips
FOR EACH ROW
BEGIN
    DECLARE v_overlap_count INT DEFAULT 0;
    
    IF NEW.trip_status != 'CANCELLED' THEN
        SELECT COUNT(*) INTO v_overlap_count
        FROM trips t
        WHERE t.bus_id = NEW.bus_id
          AND t.trip_status != 'CANCELLED'
          AND (NEW.departure_time < t.arrival_time AND NEW.arrival_time > t.departure_time);
          
        IF v_overlap_count > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Bus is already assigned to an overlapping trip.';
        END IF;
    END IF;
END$$

-- ----------------------------------------------------------------------------
-- Trigger 5: Prevent Driver Overlapping Schedules
-- Rule 6: A driver cannot be assigned to overlapping trips.
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_prevent_driver_overlap$$
CREATE TRIGGER trg_prevent_driver_overlap
BEFORE INSERT ON crew_assignments
FOR EACH ROW
BEGIN
    DECLARE v_new_dep DATETIME;
    DECLARE v_new_arr DATETIME;
    DECLARE v_overlap_count INT DEFAULT 0;
    
    SELECT departure_time, arrival_time INTO v_new_dep, v_new_arr
    FROM trips WHERE trip_id = NEW.trip_id;
    
    SELECT COUNT(*) INTO v_overlap_count
    FROM crew_assignments ca
    JOIN trips t ON ca.trip_id = t.trip_id
    WHERE ca.driver_id = NEW.driver_id
      AND t.trip_status != 'CANCELLED'
      AND (v_new_dep < t.arrival_time AND v_new_arr > t.departure_time);
      
    IF v_overlap_count > 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Driver is unavailable during this time (overlapping trip schedule).';
    END IF;
END$$

-- ----------------------------------------------------------------------------
-- Trigger 6: Prevent Conductor Overlapping Schedules
-- Rule 7: A conductor cannot be assigned to overlapping trips.
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_prevent_conductor_overlap$$
CREATE TRIGGER trg_prevent_conductor_overlap
BEFORE INSERT ON crew_assignments
FOR EACH ROW
BEGIN
    DECLARE v_new_dep DATETIME;
    DECLARE v_new_arr DATETIME;
    DECLARE v_overlap_count INT DEFAULT 0;
    
    SELECT departure_time, arrival_time INTO v_new_dep, v_new_arr
    FROM trips WHERE trip_id = NEW.trip_id;
    
    SELECT COUNT(*) INTO v_overlap_count
    FROM crew_assignments ca
    JOIN trips t ON ca.trip_id = t.trip_id
    WHERE ca.conductor_id = NEW.conductor_id
      AND t.trip_status != 'CANCELLED'
      AND (v_new_dep < t.arrival_time AND v_new_arr > t.departure_time);
      
    IF v_overlap_count > 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Conductor is unavailable during this time (overlapping trip schedule).';
    END IF;
END$$

-- ----------------------------------------------------------------------------
-- Trigger 7: Prevent Duplicate Cancellation and Validate Status
-- Rule 9: A cancelled booking cannot be cancelled again.
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_validate_cancellation$$
CREATE TRIGGER trg_validate_cancellation
BEFORE INSERT ON cancellations
FOR EACH ROW
BEGIN
    DECLARE v_current_status VARCHAR(20);
    
    SELECT booking_status INTO v_current_status
    FROM bookings
    WHERE booking_id = NEW.booking_id;
    
    IF v_current_status IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Booking does not exist.';
    ELSEIF v_current_status = 'CANCELLED' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Booking has already been cancelled.';
    END IF;
END$$

-- ----------------------------------------------------------------------------
-- Trigger 8: Cascading State Update on Cancellation
-- Automatically updates booking_status to CANCELLED and payment to REFUNDED.
-- ----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_after_cancellation_sync$$
CREATE TRIGGER trg_after_cancellation_sync
AFTER INSERT ON cancellations
FOR EACH ROW
BEGIN
    UPDATE bookings
    SET booking_status = 'CANCELLED'
    WHERE booking_id = NEW.booking_id;
    
    UPDATE payments
    SET payment_status = 'REFUNDED'
    WHERE booking_id = NEW.booking_id;
END$$

DELIMITER ;
