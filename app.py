import os
import sqlite3
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, request, send_from_directory, session


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "quickbite.db"

app = Flask(__name__)
# Set QUICKBITE_SECRET_KEY in your terminal before starting the app.
# Keep this key stable across server restarts to preserve signed sessions.
app.secret_key = os.environ["QUICKBITE_SECRET_KEY"]
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)

RESTAURANTS = [
    {
        "name": "Basil & Board",
        "type": "Italian · Pizza",
        "distance": "0.8 mi away",
        "initials": "B&B",
        "color": "#d95d39",
        "meals": [
            {"name": "Margherita Pizza", "ingredients": "Tomato, mozzarella, basil", "price": 14.5, "image": "🍕"},
            {"name": "Creamy Pesto Pasta", "ingredients": "Penne, pesto, parmesan", "price": 13.25, "image": "🍝"},
            {"name": "Garlic Knots", "ingredients": "Garlic butter, herbs, parmesan", "price": 6.0, "image": "🥖"},
        ],
    },
    {
        "name": "Green Fork Kitchen",
        "type": "Healthy · Bowls",
        "distance": "1.1 mi away",
        "initials": "GF",
        "color": "#4b8d66",
        "meals": [
            {"name": "Harvest Grain Bowl", "ingredients": "Quinoa, greens, sweet potato", "price": 12.75, "image": "🥗"},
            {"name": "Avocado Toast", "ingredients": "Sourdough, avocado, chili flakes", "price": 9.5, "image": "🥑"},
            {"name": "Berry Yogurt Cup", "ingredients": "Greek yogurt, berries, granola", "price": 7.25, "image": "🫐"},
        ],
    },
    {
        "name": "Seoul Table",
        "type": "Korean · Comfort food",
        "distance": "1.4 mi away",
        "initials": "ST",
        "color": "#7c5ba7",
        "meals": [
            {"name": "Bulgogi Rice Bowl", "ingredients": "Beef, rice, pickled vegetables", "price": 15.0, "image": "🍚"},
            {"name": "Crispy Tofu Bites", "ingredients": "Tofu, sweet chili glaze, sesame", "price": 8.5, "image": "🍢"},
            {"name": "Kimchi Fried Rice", "ingredients": "Rice, kimchi, egg, scallions", "price": 12.0, "image": "🍳"},
        ],
    },
    {
        "name": "The Burger Spot",
        "type": "Burgers · American",
        "distance": "1.7 mi away",
        "initials": "BS",
        "color": "#c58a34",
        "meals": [
            {"name": "Classic Cheeseburger", "ingredients": "Beef, cheddar, lettuce, tomato", "price": 13.5, "image": "🍔"},
            {"name": "Crispy Chicken Sandwich", "ingredients": "Chicken, slaw, pickles, sauce", "price": 12.75, "image": "🍗"},
            {"name": "Sea Salt Fries", "ingredients": "Crisp potatoes, sea salt", "price": 5.5, "image": "🍟"},
        ],
    },
    {
        "name": "Taco Luna",
        "type": "Mexican · Tacos",
        "distance": "2.0 mi away",
        "initials": "TL",
        "color": "#e08a3e",
        "meals": [
            {"name": "Chicken Street Tacos", "ingredients": "Chicken, onion, cilantro, lime", "price": 11.5, "image": "🌮"},
            {"name": "Loaded Nachos", "ingredients": "Chips, beans, cheese, salsa", "price": 10.0, "image": "🧀"},
            {"name": "Churro Bites", "ingredients": "Cinnamon sugar, chocolate dip", "price": 6.5, "image": "🥨"},
        ],
    },
    {
        "name": "Nori House",
        "type": "Japanese · Sushi",
        "distance": "2.2 mi away",
        "initials": "NH",
        "color": "#39798d",
        "meals": [
            {"name": "Salmon Poke Bowl", "ingredients": "Salmon, rice, cucumber, avocado", "price": 16.5, "image": "🍣"},
            {"name": "Spicy Tuna Roll", "ingredients": "Tuna, cucumber, spicy mayo", "price": 10.5, "image": "🍱"},
            {"name": "Edamame", "ingredients": "Steamed soybeans, sea salt", "price": 5.0, "image": "🫛"},
        ],
    },
    {
        "name": "Morning Roast",
        "type": "Breakfast · Cafe",
        "distance": "2.5 mi away",
        "initials": "MR",
        "color": "#91684a",
        "meals": [
            {"name": "Sunrise Breakfast", "ingredients": "Eggs, toast, potatoes, bacon", "price": 12.0, "image": "🍳"},
            {"name": "Blueberry Pancakes", "ingredients": "Pancakes, blueberries, maple syrup", "price": 10.5, "image": "🥞"},
            {"name": "Iced Vanilla Latte", "ingredients": "Espresso, milk, vanilla", "price": 5.75, "image": "☕"},
        ],
    },
    {
        "name": "Cedar & Spice",
        "type": "Mediterranean · Wraps",
        "distance": "2.9 mi away",
        "initials": "CS",
        "color": "#b65d56",
        "meals": [
            {"name": "Chicken Shawarma Wrap", "ingredients": "Chicken, hummus, greens, pita", "price": 11.75, "image": "🌯"},
            {"name": "Falafel Plate", "ingredients": "Falafel, tabbouleh, tahini", "price": 13.0, "image": "🧆"},
            {"name": "Hummus & Pita", "ingredients": "Chickpeas, tahini, warm pita", "price": 7.5, "image": "🫓"},
        ],
    },
]


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def current_cart_id():
    """Identify a browser's cart using its signed Flask session cookie."""
    if "cart_id" not in session:
        session["cart_id"] = uuid4().hex
        session.permanent = True
    return session["cart_id"]


def initialize_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS cart_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cart_id TEXT NOT NULL,
                name TEXT NOT NULL,
                restaurant TEXT NOT NULL,
                ingredients TEXT NOT NULL,
                price REAL NOT NULL CHECK (price >= 0),
                image TEXT NOT NULL
            )
            """
        )

        # Support a database created by the previous version of QuickBite.
        # Older cart items will have NULL cart_id and won't appear in new carts.
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(cart_items)")
        }
        if "cart_id" not in columns:
            connection.execute("ALTER TABLE cart_items ADD COLUMN cart_id TEXT")

        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_cart_items_cart_id "
            "ON cart_items(cart_id)"
        )


def cart_item_from_row(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "restaurant": row["restaurant"],
        "ingredients": row["ingredients"],
        "price": row["price"],
        "image": row["image"],
    }


@app.get("/")
def home():
    return send_from_directory(BASE_DIR, "QuickBite.html")


@app.get("/api/cart")
def get_cart():
    cart_id = current_cart_id()
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, name, restaurant, ingredients, price, image "
            "FROM cart_items WHERE cart_id = ? ORDER BY id",
            (cart_id,),
        ).fetchall()
    return jsonify([cart_item_from_row(row) for row in rows])


@app.get("/api/restaurants")
def get_restaurants():
    return jsonify(RESTAURANTS)


@app.post("/api/cart")
def add_cart_item():
    item = request.get_json(silent=True)
    required_fields = ("name", "restaurant", "ingredients", "price", "image")

    if not isinstance(item, dict) or any(
        field not in item for field in required_fields
    ):
        return jsonify({"error": "Cart item is missing required fields."}), 400

    if not isinstance(item["price"], (int, float)) or item["price"] < 0:
        return jsonify({"error": "Cart item price must be a non-negative number."}), 400

    if any(not isinstance(item[field], str) or not item[field].strip() for field in required_fields if field != "price"):
        return jsonify({"error": "Cart item text fields must not be empty."}), 400

    cart_id = current_cart_id()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO cart_items
                (cart_id, name, restaurant, ingredients, price, image)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                cart_id,
                item["name"].strip(),
                item["restaurant"].strip(),
                item["ingredients"].strip(),
                item["price"],
                item["image"].strip(),
            ),
        )
        saved_item = connection.execute(
            "SELECT id, name, restaurant, ingredients, price, image "
            "FROM cart_items WHERE id = ? AND cart_id = ?",
            (cursor.lastrowid, cart_id),
        ).fetchone()

    return jsonify(cart_item_from_row(saved_item)), 201


@app.delete("/api/cart/<int:item_id>")
def remove_cart_item(item_id):
    cart_id = current_cart_id()

    with get_connection() as connection:
        result = connection.execute(
            "DELETE FROM cart_items WHERE id = ? AND cart_id = ?",
            (item_id, cart_id)
        )

    if result.rowcount == 0:
        return jsonify({"error": "Item not found in your cart"}), 404

    return "", 204


initialize_database()


if __name__ == "__main__":
    app.run(debug=True)
