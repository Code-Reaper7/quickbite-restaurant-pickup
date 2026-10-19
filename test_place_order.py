import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import app as quickbite


MEAL = {
    "name": "Margherita Pizza",
    "restaurant": "Basil & Board",
    "ingredients": "Tomato, mozzarella, basil",
    "price": 14.5,
    "image": "pizza",
}

SIDE = {
    "name": "Garlic Knots",
    "restaurant": "Basil & Board",
    "ingredients": "Garlic butter, herbs, parmesan",
    "price": 6.0,
    "image": "bread",
}


class PlacePickupOrderTest(unittest.TestCase):
    def setUp(self):
        # Freeze server time so exact pickup-window boundaries are reproducible.
        self.now = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)
        clock = patch.object(quickbite, "datetime", wraps=datetime)
        self.mock_datetime = clock.start()
        self.mock_datetime.now.return_value = self.now
        self.addCleanup(clock.stop)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_path = quickbite.DATABASE_PATH
        quickbite.DATABASE_PATH = os.path.join(self.temp_dir.name, "test.db")
        quickbite.initialize_database()
        self.client = quickbite.app.test_client()

    def tearDown(self):
        quickbite.DATABASE_PATH = self.original_path
        self.temp_dir.cleanup()

    def add_item(self, item):
        response = self.client.post("/api/cart", json=item)
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def place_order(self, client=None, pickup_time=None):
        client = client if client is not None else self.client
        pickup_time = pickup_time if pickup_time is not None else self.now + timedelta(hours=1)
        return client.post("/api/orders", json={"pickupTime": pickup_time.isoformat()})

    def test_rejects_empty_cart(self):
        response = self.place_order()

        self.assertEqual(response.status_code, 400)
        self.assertIn("empty", response.get_json()["error"].lower())
        with quickbite.get_connection() as connection:
            order_count = connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        self.assertEqual(order_count, 0)

    def test_saves_order_with_unique_id_and_received_status(self):
        self.add_item(MEAL)
        self.add_item(SIDE)

        first = self.place_order()
        self.assertEqual(first.status_code, 201)
        first_order = first.get_json()

        self.assertIsInstance(first_order["id"], int)
        self.assertEqual(first_order["status"], "Received")
        self.assertAlmostEqual(first_order["total"], 20.5)
        self.assertEqual(first_order["pickupTime"], (self.now + timedelta(hours=1)).isoformat())
        self.assertEqual(
            [item["name"] for item in first_order["items"]],
            ["Margherita Pizza", "Garlic Knots"],
        )
        self.assertEqual(self.client.get("/api/cart").get_json(), [])

        with quickbite.get_connection() as connection:
            saved = connection.execute(
                "SELECT id, status, total, pickup_time FROM orders WHERE id = ?",
                (first_order["id"],),
            ).fetchone()
            saved_items = connection.execute(
                "SELECT name, restaurant, price FROM order_items WHERE order_id = ? ORDER BY id",
                (first_order["id"],),
            ).fetchall()

        self.assertEqual(saved["status"], "Received")
        self.assertAlmostEqual(saved["total"], 20.5)
        self.assertEqual(saved["pickup_time"], first_order["pickupTime"])
        self.assertEqual(saved_items[0]["restaurant"], "Basil & Board")
        self.assertEqual(len(saved_items), 2)

        self.add_item(MEAL)
        second = self.place_order()
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(second.get_json()["id"], first_order["id"])
        self.assertEqual(second.get_json()["status"], "Received")

    def test_empty_cart_after_order_cannot_be_submitted_again(self):
        self.add_item(MEAL)
        placed = self.place_order()
        self.assertEqual(placed.status_code, 201)

        rejected = self.place_order()
        self.assertEqual(rejected.status_code, 400)
        self.assertIn("empty", rejected.get_json()["error"].lower())

    def test_rejects_invalid_pickup_times_without_changing_cart_or_orders(self):
        self.add_item(MEAL)
        original_cart = self.client.get("/api/cart").get_json()
        cases = [
            ("missing JSON", None, "select"),
            ("missing field", {}, "select"),
            ("wrong payload type", [], "select"),
            ("null time", {"pickupTime": None}, "select"),
            ("numeric time", {"pickupTime": 123}, "select"),
            ("malformed time", {"pickupTime": "not-a-date"}, "valid"),
            ("no timezone", {"pickupTime": "2026-10-19T13:00:00"}, "timezone"),
        ]
        for label, instant, message in [
            ("past", self.now - timedelta(hours=1), "30 minutes"),
            ("too soon", self.now + timedelta(minutes=15), "30 minutes"),
            ("just before minimum", self.now + timedelta(minutes=30, microseconds=-1), "30 minutes"),
            ("just after maximum", self.now + timedelta(days=7, microseconds=1), "7 days"),
            ("off quarter-hour", self.now + timedelta(minutes=61), "15-minute"),
            ("nonzero seconds", self.now + timedelta(hours=1, seconds=1), "15-minute"),
            ("nonzero microseconds", self.now + timedelta(hours=1, microseconds=1), "15-minute"),
        ]:
            cases.append((label, {"pickupTime": instant.isoformat()}, message))

        for label, payload, message in cases:
            with self.subTest(case=label):
                response = self.client.post("/api/orders", json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertIn(message, response.get_json()["error"].lower())
                self.assertEqual(self.client.get("/api/cart").get_json(), original_cart)
                with quickbite.get_connection() as connection:
                    for table in ("orders", "order_items"):
                        self.assertEqual(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], 0)

    def test_accepts_exact_pickup_window_boundaries(self):
        for instant in (self.now + timedelta(minutes=30), self.now + timedelta(days=7)):
            with self.subTest(pickup_time=instant.isoformat()):
                self.add_item(MEAL)
                response = self.place_order(pickup_time=instant)
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.get_json()["pickupTime"], instant.isoformat())

    def test_normalizes_timezone_offset_and_accepts_z_suffix(self):
        for timestamp in ("2026-10-19T09:00:00-04:00", "2026-10-19T13:00:00Z"):
            with self.subTest(timestamp=timestamp):
                self.add_item(MEAL)
                response = self.client.post("/api/orders", json={"pickupTime": timestamp})
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.get_json()["pickupTime"], "2026-10-19T13:00:00+00:00")

    def test_checkout_does_not_use_or_clear_another_sessions_cart(self):
        other_client = quickbite.app.test_client()
        self.add_item(MEAL)
        self.assertEqual(other_client.post("/api/cart", json=SIDE).status_code, 201)
        other_cart = other_client.get("/api/cart").get_json()

        response = self.place_order()
        self.assertEqual(response.status_code, 201)
        self.assertEqual([item["name"] for item in response.get_json()["items"]], [MEAL["name"]])
        self.assertEqual(response.get_json()["total"], MEAL["price"])
        self.assertEqual(self.client.get("/api/cart").get_json(), [])
        self.assertEqual(other_client.get("/api/cart").get_json(), other_cart)

    def test_failed_item_save_rolls_back_order_and_preserves_cart(self):
        self.add_item(MEAL)
        original_cart = self.client.get("/api/cart").get_json()
        with quickbite.get_connection() as connection:
            connection.execute("""
                CREATE TRIGGER simulate_item_save_failure
                BEFORE INSERT ON order_items
                BEGIN
                    SELECT RAISE(ABORT, 'simulated item save failure');
                END
            """)

        # Propagate the deliberate database failure rather than logging a 500.
        with patch.dict(quickbite.app.config, {"TESTING": True}):
            with self.assertRaises(sqlite3.IntegrityError):
                self.place_order()

        with quickbite.get_connection() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM order_items").fetchone()[0], 0)
        self.assertEqual(self.client.get("/api/cart").get_json(), original_cart)


if __name__ == "__main__":
    unittest.main()
