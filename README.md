# quickbite-restaurant-pickup
Scrum-based restaurant ordering and pickup web application

## Run QuickBite locally

1. Install the Flask dependency:

   ```text
   pip install -r requirements.txt
   ```

2. Start the local backend:

   ```text
   python app.py
   ```

3. Open `http://127.0.0.1:5000` in a browser.

The Flask backend stores cart items in the local `quickbite.db` SQLite file. The
database is created automatically the first time the app starts.
