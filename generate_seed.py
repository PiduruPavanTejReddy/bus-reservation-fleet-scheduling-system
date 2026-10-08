# Script to generate comprehensive, realistic seed data for bus_fleet_db
from werkzeug.security import generate_password_hash
import random
from datetime import datetime, timedelta

def generate_seed_sql():
    sql = []
    sql.append("-- ============================================================================")
    sql.append("-- BUS RESERVATION AND FLEET SCHEDULING SYSTEM")
    sql.append("-- Comprehensive Seed Data (seed_data.sql)")
    sql.append("-- Target DBMS: MySQL 8.0+")
    sql.append("-- ============================================================================\n")
    sql.append("USE bus_fleet_db;\n")
    sql.append("SET FOREIGN_KEY_CHECKS = 0;\n")
    sql.append("TRUNCATE TABLE payments;")
    sql.append("TRUNCATE TABLE cancellations;")
    sql.append("TRUNCATE TABLE bookings;")
    sql.append("TRUNCATE TABLE fares;")
    sql.append("TRUNCATE TABLE crew_assignments;")
    sql.append("TRUNCATE TABLE trips;")
    sql.append("TRUNCATE TABLE seats;")
    sql.append("TRUNCATE TABLE route_stops;")
    sql.append("TRUNCATE TABLE stops;")
    sql.append("TRUNCATE TABLE routes;")
    sql.append("TRUNCATE TABLE conductors;")
    sql.append("TRUNCATE TABLE drivers;")
    sql.append("TRUNCATE TABLE buses;")
    sql.append("TRUNCATE TABLE passengers;")
    sql.append("TRUNCATE TABLE admin_users;\n")
    
    # 1. Admin Users
    admin_hash = generate_password_hash("admin123")
    disp_hash = generate_password_hash("dispatch123")
    sql.append("-- 1. ADMIN USERS")
    sql.append("INSERT INTO admin_users (username, password_hash, full_name, role) VALUES")
    sql.append(f"('admin', '{admin_hash}', 'System Administrator', 'ADMIN'),")
    sql.append(f"('dispatcher1', '{disp_hash}', 'Ramesh Varma', 'DISPATCHER'),")
    sql.append(f"('operator1', '{disp_hash}', 'Sneha Reddy', 'OPERATOR');\n")

    # 2. Buses (12 buses)
    buses = [
        (1, 'TS09UB4521', 'BUS-101', 'Volvo Multi-Axle', 40, 'ACTIVE'),
        (2, 'TS07UA8912', 'BUS-102', 'AC Sleeper', 30, 'ACTIVE'),
        (3, 'AP04TX7734', 'BUS-103', 'AC Seater', 40, 'ACTIVE'),
        (4, 'AP16TY1290', 'BUS-104', 'Non-AC Seater', 45, 'ACTIVE'),
        (5, 'KA01MJ6781', 'BUS-105', 'Volvo Multi-Axle', 40, 'ACTIVE'),
        (6, 'KA05NF4321', 'BUS-106', 'Electric AC', 36, 'ACTIVE'),
        (7, 'TN02AB9012', 'BUS-107', 'AC Sleeper', 30, 'ACTIVE'),
        (8, 'TN09CD5543', 'BUS-108', 'AC Seater', 40, 'ACTIVE'),
        (9, 'TS08EE1122', 'BUS-109', 'Volvo Multi-Axle', 40, 'ACTIVE'),
        (10, 'AP09FF3344', 'BUS-110', 'Non-AC Seater', 45, 'ACTIVE'),
        (11, 'TS10GG5566', 'BUS-111', 'AC Sleeper', 30, 'MAINTENANCE'),
        (12, 'KA03HH7788', 'BUS-112', 'Electric AC', 36, 'ACTIVE')
    ]
    sql.append("-- 2. BUSES")
    sql.append("INSERT INTO buses (bus_id, registration_number, bus_number, bus_type, total_seats, status) VALUES")
    bus_lines = [f"({b[0]}, '{b[1]}', '{b[2]}', '{b[3]}', {b[4]}, '{b[5]}')" for b in buses]
    sql.append(",\n".join(bus_lines) + ";\n")

    # 3. Seats for each bus
    sql.append("-- 3. SEATS INVENTORY")
    seat_rows = []
    seat_id = 1
    for b in buses:
        b_id = b[0]
        b_type = b[3]
        total_s = b[4]
        
        if 'Sleeper' in b_type:
            # 30 seats: 15 Lower, 15 Upper (L1..L15, U1..U15)
            for i in range(1, 16):
                stype = 'SLEEPER_LOWER' if i % 2 != 0 else 'WINDOW'
                seat_rows.append(f"({seat_id}, {b_id}, 'L{i:02d}', '{stype}', 'LOWER')")
                seat_id += 1
            for i in range(1, 16):
                stype = 'SLEEPER_UPPER' if i % 2 != 0 else 'WINDOW'
                seat_rows.append(f"({seat_id}, {b_id}, 'U{i:02d}', '{stype}', 'UPPER')")
                seat_id += 1
        else:
            # Seater: S01..S<total_s>
            for i in range(1, total_s + 1):
                stype = 'WINDOW' if (i % 4 == 1 or i % 4 == 0) else 'AISLE'
                seat_rows.append(f"({seat_id}, {b_id}, 'S{i:02d}', '{stype}', 'LOWER')")
                seat_id += 1

    sql.append("-- 3. SEATS INVENTORY")
    for i in range(0, len(seat_rows), 50):
        chunk = seat_rows[i:i+50]
        sql.append("INSERT INTO seats (seat_id, bus_id, seat_number, seat_type, deck) VALUES")
        sql.append(",\n".join(chunk) + ";")
    sql.append("")

    # 4. Routes (9 routes)
    routes = [
        (1, 'Hyderabad to Bengaluru Express', 'Hyderabad', 'Bengaluru', 570.00, 9.50),
        (2, 'Bengaluru to Hyderabad Express', 'Bengaluru', 'Hyderabad', 570.00, 9.50),
        (3, 'Hyderabad to Vijayawada Superfast', 'Hyderabad', 'Vijayawada', 275.00, 5.00),
        (4, 'Vijayawada to Hyderabad Superfast', 'Vijayawada', 'Hyderabad', 275.00, 5.00),
        (5, 'Vijayawada to Chennai Classic', 'Vijayawada', 'Chennai', 450.00, 8.00),
        (6, 'Chennai to Bengaluru Highway', 'Chennai', 'Bengaluru', 350.00, 6.00),
        (7, 'Hyderabad to Tirupati Pilgrim Special', 'Hyderabad', 'Tirupati', 555.00, 10.00),
        (8, 'Tirupati to Bengaluru Deluxe', 'Tirupati', 'Bengaluru', 250.00, 4.50),
        (9, 'Hyderabad to Nellore Coastal Rider', 'Hyderabad', 'Nellore', 450.00, 7.50)
    ]
    sql.append("-- 4. ROUTES")
    sql.append("INSERT INTO routes (route_id, route_name, source, destination, distance_km, estimated_duration_hours) VALUES")
    sql.append(",\n".join([f"({r[0]}, '{r[1]}', '{r[2]}', '{r[3]}', {r[4]}, {r[5]})" for r in routes]) + ";\n")

    # 5. Stops (24 stops)
    stops = [
        (1, 'MGBS Central', 'Hyderabad', 'Mahatma Gandhi Bus Station, Gowliguda'),
        (2, 'Ameerpet Metro Hub', 'Hyderabad', 'Near Metro Pillar A102'),
        (3, 'Miyapur Cross Roads', 'Hyderabad', 'Allwyn Colony Junction'),
        (4, 'Gachibowli ORR', 'Hyderabad', 'Outer Ring Road Bus Bay'),
        (5, 'LB Nagar Ring Road', 'Hyderabad', 'Sagar Ring Road Junction'),
        (6, 'Suryapet Highway Stop', 'Suryapet', 'NH-65 Highway Food Court'),
        (7, 'Pandit Nehru Bus Station', 'Vijayawada', 'PNBS Terminal Platform 12'),
        (8, 'Benz Circle', 'Vijayawada', 'MG Road Flyover'),
        (9, 'NTR Bus Station Guntur', 'Guntur', 'Main Gate Guntur RTC'),
        (10, 'Ongole RTC Complex', 'Ongole', 'NH-16 Bypass Depot'),
        (11, 'Nellore RTC Complex', 'Nellore', 'Grand Trunk Road'),
        (12, 'Kavali Bypass', 'Nellore', 'Highway Toll Gate Plaza'),
        (13, 'CMBT Koyambedu', 'Chennai', 'Chennai Mofussil Bus Terminus Platform 4'),
        (14, 'Guindy Kathipara', 'Chennai', 'Kathipara Junction'),
        (15, 'Tirupati Central Bus Stand', 'Tirupati', 'Opposite Railway Station'),
        (16, 'Alipiri Gate', 'Tirupati', 'Tirumala Footpath Entry'),
        (17, 'Majestic Kempegowda', 'Bengaluru', 'KSRTC Terminal 1'),
        (18, 'Electronic City Toll', 'Bengaluru', 'Phase 1 Elevated Flyover'),
        (19, 'Silk Board Junction', 'Bengaluru', 'Hosur Road Bus Shelter'),
        (20, 'Kurnool City RTC', 'Kurnool', 'Bellary Chowrasta'),
        (21, 'Anantapur Clock Tower', 'Anantapur', 'Subhash Road Junction'),
        (22, 'Chittoor Old Bus Stand', 'Chittoor', 'High Street Depot'),
        (23, 'Kanchipuram Bypass', 'Kanchipuram', 'NH-48 Overbridge'),
        (24, 'Sriperumbudur Hub', 'Sriperumbudur', 'SIPCOT Industrial Area')
    ]
    sql.append("-- 5. STOPS")
    sql.append("INSERT INTO stops (stop_id, stop_name, city, location_landmark) VALUES")
    sql.append(",\n".join([f"({s[0]}, '{s[1]}', '{s[2]}', '{s[3]}')" for s in stops]) + ";\n")

    # 6. Route Stops (Intermediates)
    route_stops = [
        # Route 1: Hyd -> Blr (Stops: 1:MGBS, 4:Gachibowli, 20:Kurnool, 21:Anantapur, 17:Majestic, 18:Electronic City)
        (1, 1, 1, 0, 15),
        (1, 4, 2, 45, 55),
        (1, 20, 3, 210, 225),
        (1, 21, 4, 360, 375),
        (1, 17, 5, 540, 555),
        (1, 18, 6, 570, 570),
        # Route 3: Hyd -> Vja (Stops: 1:MGBS, 5:LB Nagar, 6:Suryapet, 7:PNBS Vijayawada, 8:Benz Circle)
        (3, 1, 1, 0, 15),
        (3, 5, 2, 35, 45),
        (3, 6, 3, 150, 165),
        (3, 7, 4, 285, 300),
        (3, 8, 5, 310, 310),
        # Route 5: Vja -> Chennai (Stops: 7:PNBS, 9:Guntur, 10:Ongole, 11:Nellore, 13:CMBT Chennai)
        (5, 7, 1, 0, 15),
        (5, 9, 2, 45, 60),
        (5, 10, 3, 180, 195),
        (5, 11, 4, 300, 315),
        (5, 13, 5, 480, 480),
        # Route 6: Chennai -> Blr (Stops: 13:CMBT, 24:Sriperumbudur, 23:Kanchipuram, 19:Silk Board, 17:Majestic)
        (6, 13, 1, 0, 15),
        (6, 24, 2, 50, 60),
        (6, 23, 3, 110, 120),
        (6, 19, 4, 330, 345),
        (6, 17, 5, 360, 360),
        # Route 7: Hyd -> Tirupati (Stops: 1:MGBS, 20:Kurnool, 15:Tirupati Central, 16:Alipiri)
        (7, 1, 1, 0, 15),
        (7, 20, 2, 210, 225),
        (7, 15, 3, 580, 595),
        (7, 16, 4, 600, 600),
        # Route 8: Tirupati -> Blr (Stops: 15:Tirupati, 22:Chittoor, 18:Electronic City, 17:Majestic)
        (8, 15, 1, 0, 15),
        (8, 22, 2, 90, 105),
        (8, 18, 3, 240, 255),
        (8, 17, 4, 270, 270),
        # Route 9: Hyd -> Nellore (Stops: 1:MGBS, 5:LB Nagar, 6:Suryapet, 10:Ongole, 11:Nellore)
        (9, 1, 1, 0, 15),
        (9, 5, 2, 35, 45),
        (9, 6, 3, 150, 165),
        (9, 10, 4, 330, 345),
        (9, 11, 5, 450, 450)
    ]
    sql.append("-- 6. ROUTE STOPS")
    sql.append("INSERT INTO route_stops (route_id, stop_id, stop_order, arrival_offset_mins, departure_offset_mins) VALUES")
    sql.append(",\n".join([f"({rs[0]}, {rs[1]}, {rs[2]}, {rs[3]}, {rs[4]})" for rs in route_stops]) + ";\n")

    # 7. Drivers (12 drivers)
    drivers = [
        (1, 'Venkatesh Rao', '9848011221', 'DL-TS-2015-0012984', 12, 'ACTIVE'),
        (2, 'Subba Raju', '9848022332', 'DL-AP-2016-0045123', 10, 'ACTIVE'),
        (3, 'Narayana Murthy', '9848033443', 'DL-KA-2014-0099881', 14, 'ACTIVE'),
        (4, 'Srinivasa Reddy', '9848044554', 'DL-TS-2017-0033221', 8, 'ACTIVE'),
        (5, 'Murugan Selvam', '9848055665', 'DL-TN-2013-0077665', 15, 'ACTIVE'),
        (6, 'Ravi Kumar', '9848066776', 'DL-TS-2018-0055443', 7, 'ACTIVE'),
        (7, 'Appala Naidu', '9848077887', 'DL-AP-2012-0011223', 16, 'ACTIVE'),
        (8, 'Basavaraj Patil', '9848088998', 'DL-KA-2019-0066778', 6, 'ACTIVE'),
        (9, 'Kalyan Chakravarthy', '9848099009', 'DL-AP-2015-0088990', 11, 'ACTIVE'),
        (10, 'Govind Swamy', '9848100110', 'DL-TN-2016-0022334', 9, 'ACTIVE'),
        (11, 'Mahesh Goud', '9848111221', 'DL-TS-2020-0044556', 5, 'ACTIVE'),
        (12, 'Chandrasekhar Reddy', '9848122332', 'DL-AP-2011-0077889', 17, 'ACTIVE')
    ]
    sql.append("-- 7. DRIVERS")
    sql.append("INSERT INTO drivers (driver_id, name, phone, license_number, experience_years, status) VALUES")
    sql.append(",\n".join([f"({d[0]}, '{d[1]}', '{d[2]}', '{d[3]}', {d[4]}, '{d[5]}')" for d in drivers]) + ";\n")

    # 8. Conductors (12 conductors)
    conductors = [
        (1, 'Kishore Babu', '9701011221', 'COND-TS-101', 'ACTIVE'),
        (2, 'Prasad Varma', '9701022332', 'COND-AP-102', 'ACTIVE'),
        (3, 'Manjunath Swamy', '9701033443', 'COND-KA-103', 'ACTIVE'),
        (4, 'Prakash Rao', '9701044554', 'COND-TS-104', 'ACTIVE'),
        (5, 'Muthu Krishnan', '9701055665', 'COND-TN-105', 'ACTIVE'),
        (6, 'Sudhakar Reddy', '9701066776', 'COND-AP-106', 'ACTIVE'),
        (7, 'Suresh Kumar', '9701077887', 'COND-TS-107', 'ACTIVE'),
        (8, 'Anand Gowda', '9701088998', 'COND-KA-108', 'ACTIVE'),
        (9, 'Balaram Krishna', '9701099009', 'COND-AP-109', 'ACTIVE'),
        (10, 'Saravanan Perumal', '9701100110', 'COND-TN-110', 'ACTIVE'),
        (11, 'Devaiah Naidu', '9701111221', 'COND-AP-111', 'ACTIVE'),
        (12, 'Hanumantha Rao', '9701122332', 'COND-TS-112', 'ACTIVE')
    ]
    sql.append("-- 8. CONDUCTORS")
    sql.append("INSERT INTO conductors (conductor_id, name, phone, employee_code, status) VALUES")
    sql.append(",\n".join([f"({c[0]}, '{c[1]}', '{c[2]}', '{c[3]}', '{c[4]}')" for c in conductors]) + ";\n")

    # 9. Passengers (35 passengers)
    passengers = [
        (1, 'Arun Karthik', '9849001001', 'arun.karthik@example.com', 'MALE', 29),
        (2, 'Divya Sree', '9849001002', 'divya.sree@example.com', 'FEMALE', 26),
        (3, 'Sai Charan Teja', '9849001003', 'sai.charan@example.com', 'MALE', 24),
        (4, 'Harika Chowdary', '9849001004', 'harika.c@example.com', 'FEMALE', 27),
        (5, 'Vikramaditya Rao', '9849001005', 'vikram.rao@example.com', 'MALE', 35),
        (6, 'Meenakshi Sundaram', '9849001006', 'meenakshi.s@example.com', 'FEMALE', 32),
        (7, 'Rajesh Kannan', '9849001007', 'rajesh.k@example.com', 'MALE', 41),
        (8, 'Ananya Sharma', '9849001008', 'ananya.sharma@example.com', 'FEMALE', 23),
        (9, 'Pradeep Varma', '9849001009', 'pradeep.v@example.com', 'MALE', 38),
        (10, 'Swathi Reddy', '9849001010', 'swathi.reddy@example.com', 'FEMALE', 30),
        (11, 'Manoj Kumar', '9849001011', 'manoj.kumar@example.com', 'MALE', 33),
        (12, 'Pooja Hegde', '9849001012', 'pooja.h@example.com', 'FEMALE', 28),
        (13, 'Deepak Naidu', '9849001013', 'deepak.naidu@example.com', 'MALE', 31),
        (14, 'Sandhya Rani', '9849001014', 'sandhya.rani@example.com', 'FEMALE', 45),
        (15, 'Kiranmai Pasupuleti', '9849001015', 'kiranmai.p@example.com', 'FEMALE', 25),
        (16, 'Naveen Chandra', '9849001016', 'naveen.c@example.com', 'MALE', 27),
        (17, 'Lalitha Devi', '9849001017', 'lalitha.devi@example.com', 'FEMALE', 52),
        (18, 'Gautham Krishna', '9849001018', 'gautham.k@example.com', 'MALE', 22),
        (19, 'Bhavana Menon', '9849001019', 'bhavana.menon@example.com', 'FEMALE', 29),
        (20, 'Siddharth Rao', '9849001020', 'siddharth.rao@example.com', 'MALE', 36),
        (21, 'Pavani Kumari', '9849001021', 'pavani.k@example.com', 'FEMALE', 34),
        (22, 'Vamsi Krishna', '9849001022', 'vamsi.k@example.com', 'MALE', 30),
        (23, 'Kavya Madhavan', '9849001023', 'kavya.m@example.com', 'FEMALE', 26),
        (24, 'Ramesh Babu', '9849001024', 'ramesh.babu@example.com', 'MALE', 48),
        (25, 'Radhika Apte', '9849001025', 'radhika.a@example.com', 'FEMALE', 37),
        (26, 'Suresh Raina', '9849001026', 'suresh.r@example.com', 'MALE', 39),
        (27, 'Lavanya Tripathi', '9849001027', 'lavanya.t@example.com', 'FEMALE', 25),
        (28, 'Teja Sajja', '9849001028', 'teja.sajja@example.com', 'MALE', 24),
        (29, 'Roopa Ganguly', '9849001029', 'roopa.g@example.com', 'FEMALE', 42),
        (30, 'Ajay Dev', '9849001030', 'ajay.dev@example.com', 'MALE', 31),
        (31, 'Snehalatha', '9849001031', 'snehalatha@example.com', 'FEMALE', 50),
        (32, 'Tarun Kumar', '9849001032', 'tarun.k@example.com', 'MALE', 28),
        (33, 'Madhuri Dixit', '9849001033', 'madhuri.d@example.com', 'FEMALE', 46),
        (34, 'Varun Sandesh', '9849001034', 'varun.s@example.com', 'MALE', 32),
        (35, 'Nandini Reddy', '9849001035', 'nandini.r@example.com', 'FEMALE', 29)
    ]
    sql.append("-- 9. PASSENGERS")
    sql.append("INSERT INTO passengers (passenger_id, name, phone, email, gender, age) VALUES")
    sql.append(",\n".join([f"({p[0]}, '{p[1]}', '{p[2]}', '{p[3]}', '{p[4]}', {p[5]})" for p in passengers]) + ";\n")

    # 10. Trips (32 realistic trips)
    # Date baseline: 2026-10-01 to 2026-10-15
    trips = [
        # Past Completed Trips
        (1, 1, 1, '2026-10-01 21:00:00', '2026-10-02 06:30:00', 'COMPLETED'),
        (2, 3, 3, '2026-10-01 06:00:00', '2026-10-01 11:00:00', 'COMPLETED'),
        (3, 4, 3, '2026-10-01 14:00:00', '2026-10-01 19:00:00', 'COMPLETED'),
        (4, 5, 2, '2026-10-02 21:00:00', '2026-10-03 06:30:00', 'COMPLETED'),
        (5, 7, 5, '2026-10-02 20:30:00', '2026-10-03 04:30:00', 'COMPLETED'),
        (6, 2, 7, '2026-10-03 19:00:00', '2026-10-04 05:00:00', 'COMPLETED'),
        (7, 8, 6, '2026-10-03 06:30:00', '2026-10-03 12:30:00', 'COMPLETED'),
        (8, 6, 8, '2026-10-04 14:00:00', '2026-10-04 18:30:00', 'COMPLETED'),
        (9, 9, 9, '2026-10-04 22:00:00', '2026-10-05 05:30:00', 'COMPLETED'),
        (10, 10, 4, '2026-10-05 07:00:00', '2026-10-05 12:00:00', 'COMPLETED'),

        # Current & Imminent Trips (2026-10-08 to 2026-10-10)
        (11, 1, 1, '2026-10-08 21:00:00', '2026-10-09 06:30:00', 'PUBLISHED'),
        (12, 2, 7, '2026-10-08 20:00:00', '2026-10-09 06:00:00', 'PUBLISHED'),
        (13, 3, 3, '2026-10-08 16:00:00', '2026-10-08 21:00:00', 'PUBLISHED'),
        (14, 5, 2, '2026-10-08 22:00:00', '2026-10-09 07:30:00', 'PUBLISHED'),
        (15, 6, 8, '2026-10-09 06:00:00', '2026-10-09 10:30:00', 'PUBLISHED'),
        (16, 7, 5, '2026-10-09 21:30:00', '2026-10-10 05:30:00', 'PUBLISHED'),
        (17, 8, 6, '2026-10-09 15:00:00', '2026-10-09 21:00:00', 'PUBLISHED'),
        (18, 9, 9, '2026-10-09 23:00:00', '2026-10-10 06:30:00', 'PUBLISHED'),
        (19, 4, 3, '2026-10-10 06:30:00', '2026-10-10 11:30:00', 'PUBLISHED'),
        (20, 10, 4, '2026-10-10 14:00:00', '2026-10-10 19:00:00', 'PUBLISHED'),

        # Future Trips (2026-10-11 to 2026-10-16)
        (21, 1, 1, '2026-10-11 21:00:00', '2026-10-12 06:30:00', 'PUBLISHED'),
        (22, 2, 7, '2026-10-11 20:00:00', '2026-10-12 06:00:00', 'PUBLISHED'),
        (23, 5, 2, '2026-10-11 22:00:00', '2026-10-12 07:30:00', 'PUBLISHED'),
        (24, 7, 5, '2026-10-12 21:30:00', '2026-10-13 05:30:00', 'PUBLISHED'),
        (25, 8, 6, '2026-10-12 07:00:00', '2026-10-12 13:00:00', 'PUBLISHED'),
        (26, 9, 9, '2026-10-12 22:30:00', '2026-10-13 06:00:00', 'PUBLISHED'),
        (27, 3, 3, '2026-10-13 07:00:00', '2026-10-13 12:00:00', 'PUBLISHED'),
        (28, 4, 4, '2026-10-13 15:00:00', '2026-10-13 20:00:00', 'PUBLISHED'),
        (29, 6, 8, '2026-10-14 06:30:00', '2026-10-14 11:00:00', 'PUBLISHED'),
        (30, 12, 1, '2026-10-14 20:30:00', '2026-10-15 06:00:00', 'PUBLISHED'),
        (31, 1, 1, '2026-10-15 21:00:00', '2026-10-16 06:30:00', 'SCHEDULED'),
        (32, 2, 7, '2026-10-15 19:30:00', '2026-10-16 05:30:00', 'SCHEDULED')
    ]
    sql.append("-- 10. TRIPS")
    sql.append("INSERT INTO trips (trip_id, bus_id, route_id, departure_time, arrival_time, trip_status) VALUES")
    sql.append(",\n".join([f"({t[0]}, {t[1]}, {t[2]}, '{t[3]}', '{t[4]}', '{t[5]}')" for t in trips]) + ";\n")

    # 11. Fares (1 per trip)
    fares = [
        (1, 1, 1150.00), (2, 2, 650.00), (3, 3, 550.00), (4, 4, 1150.00), (5, 5, 950.00),
        (6, 6, 1050.00), (7, 7, 750.00), (8, 8, 500.00), (9, 9, 850.00), (10, 10, 550.00),
        (11, 11, 1200.00), (12, 12, 1100.00), (13, 13, 680.00), (14, 14, 1200.00), (15, 15, 520.00),
        (16, 16, 980.00), (17, 17, 780.00), (18, 18, 880.00), (19, 19, 580.00), (20, 20, 580.00),
        (21, 21, 1200.00), (22, 22, 1100.00), (23, 23, 1200.00), (24, 24, 980.00), (25, 25, 780.00),
        (26, 26, 880.00), (27, 27, 680.00), (28, 28, 580.00), (29, 29, 520.00), (30, 30, 1250.00),
        (31, 31, 1200.00), (32, 32, 1100.00)
    ]
    sql.append("-- 11. FARES")
    sql.append("INSERT INTO fares (fare_id, trip_id, amount) VALUES")
    sql.append(",\n".join([f"({f[0]}, {f[1]}, {f[2]})" for f in fares]) + ";\n")

    # 12. Crew Assignments (1 per trip)
    # Ensure no driver/conductor overlap on active trips!
    # Drivers 1..12, Conductors 1..12
    crew = []
    ca_id = 1
    for t in trips:
        t_id = t[0]
        # Distribute crew based on trip id
        d_id = ((t_id - 1) % 12) + 1
        c_id = ((t_id + 5) % 12) + 1
        crew.append(f"({ca_id}, {t_id}, {d_id}, {c_id})")
        ca_id += 1
    sql.append("-- 12. CREW ASSIGNMENTS")
    sql.append("INSERT INTO crew_assignments (assignment_id, trip_id, driver_id, conductor_id) VALUES")
    sql.append(",\n".join(crew) + ";\n")

    # 13. Bookings (65 realistic bookings)
    # Map trip_id to bus_id to choose valid seat_ids!
    trip_to_bus = {t[0]: t[1] for t in trips}
    
    # We need a quick map of bus_id -> list of seat_ids
    # Bus 1 has seats 1..40, Bus 2 has seats 41..70, Bus 3 has seats 71..110, etc.
    bus_seats_map = {}
    current_sid = 1
    for b in buses:
        b_id = b[0]
        cnt = b[4]
        bus_seats_map[b_id] = list(range(current_sid, current_sid + cnt))
        current_sid += cnt

    bookings = []
    bk_id = 1
    # Sample bookings across trips 1, 2, 3, 5, 6, 11, 12, 13, 14, 15, 16, 21, 22
    trip_sample_counts = {
        1: 8, 2: 6, 3: 5, 5: 6, 6: 5, 
        11: 12, 12: 8, 13: 7, 14: 6, 15: 4, 16: 5,
        21: 4, 22: 3
    }
    
    fare_map = {f[1]: f[2] for f in fares}
    
    cancellation_candidate_ids = []

    for t_id, count in trip_sample_counts.items():
        b_id = trip_to_bus[t_id]
        seats_available = bus_seats_map[b_id][:count]
        f_amount = fare_map[t_id]
        
        for idx, s_id in enumerate(seats_available):
            p_id = ((bk_id - 1) % 35) + 1
            ref = f"BKG-{2026000 + bk_id}"
            
            # All bookings start CONFIRMED; trigger trg_after_cancellation_sync will update to CANCELLED upon cancellation insertion
            status = 'CONFIRMED'
            if bk_id in [4, 9, 14, 28, 35, 42, 55]:
                cancellation_candidate_ids.append((bk_id, f_amount))
                
            b_time = f"2026-10-0{min(7, (bk_id % 7) + 1):02d} {10 + (bk_id % 10):02d}:15:00"
            bookings.append((bk_id, ref, t_id, p_id, s_id, b_time, status, f_amount))
            bk_id += 1

    sql.append("-- 13. BOOKINGS")
    sql.append("INSERT INTO bookings (booking_id, booking_reference, trip_id, passenger_id, seat_id, booking_time, booking_status, total_amount) VALUES")
    sql.append(",\n".join([f"({b[0]}, '{b[1]}', {b[2]}, {b[3]}, {b[4]}, '{b[5]}', '{b[6]}', {b[7]})" for b in bookings]) + ";\n")

    # 14. Cancellations (7 cancellations)
    cancellations = [
        (1, 4, '2026-10-01 12:00:00', 'Medical emergency in family', 100.00, fare_map[1] * 1.0),
        (2, 9, '2026-10-01 04:30:00', 'Sudden change in meeting schedule', 75.00, fare_map[2] * 0.75),
        (3, 14, '2026-10-01 11:00:00', 'Booked alternate train connection', 75.00, fare_map[3] * 0.75),
        (4, 28, '2026-10-07 18:00:00', 'Flight connection rescheduled', 100.00, fare_map[11] * 1.0),
        (5, 35, '2026-10-08 09:00:00', 'Personal reasons / travel postponed', 75.00, fare_map[11] * 0.75),
        (6, 42, '2026-10-08 14:00:00', 'Severe weather alert in origin city', 50.00, fare_map[12] * 0.50),
        (7, 55, '2026-10-07 22:00:00', 'Duplicate ticket booked mistakenly', 100.00, fare_map[14] * 1.0)
    ]
    sql.append("-- 14. CANCELLATIONS")
    sql.append("INSERT INTO cancellations (cancellation_id, booking_id, cancellation_time, reason, refund_percentage, refund_amount) VALUES")
    sql.append(",\n".join([f"({c[0]}, {c[1]}, '{c[2]}', '{c[3]}', {c[4]}, {c[5]:.2f})" for c in cancellations]) + ";\n")

    # 15. Payments (1 per booking)
    methods = ['UPI', 'CREDIT_CARD', 'DEBIT_CARD', 'NET_BANKING', 'CASH']
    payments = []
    cancelled_bkids = {c[1] for c in cancellations}
    for b in bookings:
        b_id = b[0]
        amt = b[7]
        m = methods[(b_id - 1) % len(methods)]
        p_status = 'REFUNDED' if b_id in cancelled_bkids else 'PAID'
        txn = f"TXN-{20269000 + b_id}"
        p_time = b[5]
        payments.append(f"({b_id}, {b_id}, {amt}, '{m}', '{p_status}', '{p_time}', '{txn}')")

    sql.append("-- 15. PAYMENTS")
    sql.append("INSERT INTO payments (payment_id, booking_id, amount, payment_method, payment_status, payment_time, transaction_reference) VALUES")
    sql.append(",\n".join(payments) + ";\n")

    sql.append("SET FOREIGN_KEY_CHECKS = 1;\n")
    return "\n".join(sql)

if __name__ == '__main__':
    with open('database/seed_data.sql', 'w', encoding='utf-8') as f:
        f.write(generate_seed_sql())
    print("seed_data.sql generated successfully!")
