# QuickBite Restaurant Pickup

QuickBite is a Scrum-based restaurant ordering and pickup web application.

## Technologies Used

- Python and Flask
- HTML, CSS, and JavaScript
- SQLite
- Git and GitHub

## Current Features

- Browse participating restaurants
- View restaurant menus and prices
- Add food items to the shopping cart
- Display item quantities and subtotals
- Calculate the total cart price
- Maintain separate carts for different browser sessions
- Preserve cart items after refreshing the page

## Run QuickBite Locally

### 1. Install Dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 2. Configure Flask Sessions

Generate a secret key before starting the application:

```bash
export QUICKBITE_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
```

Keep the secret key private. Use the same key across server restarts to preserve existing sessions.

### 3. Start the Application

```bash
python3 app.py
```

### 4. Open the Website

Visit http://127.0.0.1:5000

If port 5000 is unavailable, run:

```bash
python3 -m flask --app app run --port 5001
```

Then visit http://127.0.0.1:5001

## Database

QuickBite uses SQLite to store shopping cart information.

The database is initialized automatically when the application starts.

Each browser session has its own shopping cart.

The local database file is excluded from Git tracking using `.gitignore`.

## Development Workflow

Our team uses GitHub Projects to manage the Product Backlog, Sprint tasks, development progress, and code reviews.

All features must meet the Definition of Done before being marked as completed.
The Flask backend stores cart items and pickup orders in the local `quickbite.db`
SQLite file. The database is created automatically the first time the app starts.
Each placed order is saved with a unique order ID and an initial status of Received.
