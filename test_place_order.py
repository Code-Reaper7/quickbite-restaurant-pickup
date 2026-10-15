import os
import tempfile
import unittest

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

    def test_rejects_empty_cart(self):
        response = self.client.post("/api/orders")

        self.assertEqual(response.status_code, 400)
        self.assertIn("empty", response.get_json()["error"].lower())
        with quickbite.get_connection() as connection:
            order_count = connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        self.assertEqual(order_count, 0)

    def test_saves_order_with_unique_id_and_received_status(self):
        self.add_item(MEAL)
        self.add_item(SIDE)

        first = self.client.post("/api/orders")
        self.assertEqual(first.status_code, 201)
        first_order = first.get_json()

        self.assertIsInstance(first_order["id"], int)
        self.assertEqual(first_order["status"], "Received")
        self.assertAlmostEqual(first_order["total"], 20.5)
        self.assertEqual(
            [item["name"] for item in first_order["items"]],
            ["Margherita Pizza", "Garlic Knots"],
        )
        self.assertEqual(self.client.get("/api/cart").get_json(), [])

        with quickbite.get_connection() as connection:
            saved = connection.execute(
                "SELECT id, status, total FROM orders WHERE id = ?",
                (first_order["id"],),
            ).fetchone()
            saved_items = connection.execute(
                "SELECT name, restaurant, price FROM order_items WHERE order_id = ? ORDER BY id",
                (first_order["id"],),
            ).fetchall()

        self.assertEqual(saved["status"], "Received")
        self.assertAlmostEqual(saved["total"], 20.5)
        self.assertEqual(saved_items[0]["restaurant"], "Basil & Board")
        self.assertEqual(len(saved_items), 2)

        self.add_item(MEAL)
        second = self.client.post("/api/orders")
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(second.get_json()["id"], first_order["id"])
        self.assertEqual(second.get_json()["status"], "Received")

    def test_empty_cart_after_order_cannot_be_submitted_again(self):
        self.add_item(MEAL)
        placed = self.client.post("/api/orders")
        self.assertEqual(placed.status_code, 201)

        rejected = self.client.post("/api/orders")
        self.assertEqual(rejected.status_code, 400)


if __name__ == "__main__":
    unittest.main()
