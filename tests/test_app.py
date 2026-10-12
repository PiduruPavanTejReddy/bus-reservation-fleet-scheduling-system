"""
Integration tests for Flask application endpoints and web workflow.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_login_page(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Sign In to Dashboard' in response.data

def test_login_and_dashboard_flow(client):
    # Perform successful admin login
    res = client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    assert res.status_code == 200
    assert b'Fleet Operations Dashboard' in res.data
    assert b'Total Buses' in res.data

def test_dispatcher_login(client):
    # Test dispatcher login
    res = client.post('/login', data={'username': 'dispatcher1', 'password': 'dispatcher123'}, follow_redirects=True)
    assert res.status_code == 200
    assert b'Fleet Operations Dashboard' in res.data

def test_operator_login(client):
    # Test operator login
    res = client.post('/login', data={'username': 'operator1', 'password': 'operator123'}, follow_redirects=True)
    assert res.status_code == 200
    assert b'Fleet Operations Dashboard' in res.data

def test_authenticated_pages(client):
    # Log in first
    client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

    endpoints = [
        ('/buses', b'Fleet Inventory List'),
        ('/routes', b'Network Routes'),
        ('/stops', b'Master Stops Directory'),
        ('/trips', b'Fleet Trip Schedule Ledger'),
        ('/crew', b'Crew & Operational Personnel'),
        ('/passengers', b'Passenger Directory'),
        ('/bookings', b'Ticket Bookings'),
        ('/cancellations', b'Cancellations & Refund Audit'),
        ('/payments', b'Payment Records'),
        ('/reports', b'DBMS Analytical Reports Suite'),
        ('/sql-demo', b'SQL Concepts & Demonstration Suite'),
        ('/search', b'Search Trip Availability')
    ]

    for url, text_marker in endpoints:
        resp = client.get(url)
        assert resp.status_code == 200, f"Failed on endpoint {url} with code {resp.status_code}"
        assert text_marker in resp.data, f"Failed to find expected content in {url}"

def test_seat_layout_page(client):
    client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
    resp = client.get('/book/11')
    assert resp.status_code == 200
    assert b'Seat Reservation & Checkout' in resp.data
    assert b'seat-item' in resp.data
