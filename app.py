from flask import Flask, jsonify, request, send_file, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os, json

app = Flask(__name__)
app.secret_key = 'freshmart-secret-key-change-in-production'
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'freshmart.db')

# ── DB helpers ────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        items_json TEXT NOT NULL,
        subtotal REAL NOT NULL,
        delivery_fee REAL NOT NULL,
        total REAL NOT NULL,
        item_count INTEGER NOT NULL,
        delivery_address TEXT DEFAULT '',
        lat REAL,
        lng REAL,
        placed_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

# ── Product Data ──────────────────────────────────────────────────────────────
PRODUCTS = [
    {"id":1,  "name":"Alphonso Mangoes",    "cat":"fruit",     "price":299, "unit":"1 kg",    "emoji":"🥭", "tag":"Seasonal",  "description":"The king of mangoes. Rich, creamy, non-fibrous texture with a distinct sweet aroma. Sourced from Ratnagiri. Perfect for eating fresh, shakes, or desserts."},
    {"id":2,  "name":"Bananas",             "cat":"fruit",     "price":49,  "unit":"6 pcs",   "emoji":"🍌", "tag":"Daily",     "description":"Sweet and nutritious ripe bananas. Rich in potassium and natural energy. Great for breakfast, smoothies, or a quick snack on the go."},
    {"id":3,  "name":"Strawberries",        "cat":"fruit",     "price":179, "unit":"250 g",   "emoji":"🍓", "tag":"Fresh",     "description":"Bright red, juicy strawberries with a sweet-tart flavour. Packed with Vitamin C and antioxidants. Excellent fresh, in yogurt, or desserts."},
    {"id":4,  "name":"Watermelon",          "cat":"fruit",     "price":89,  "unit":"1 whole", "emoji":"🍉", "tag":"Seasonal",  "description":"A whole juicy watermelon perfect for summer hydration. 92% water content makes it ideal for beating the heat. Seedless variety."},
    {"id":5,  "name":"Apples (Shimla)",     "cat":"fruit",     "price":149, "unit":"1 kg",    "emoji":"🍎", "tag":"Fresh",     "description":"Crisp and sweet Shimla apples from Himachal Pradesh orchards. Rich in fibre and Vitamin C. Great for snacking or baking."},
    {"id":6,  "name":"Grapes (Green)",      "cat":"fruit",     "price":119, "unit":"500 g",   "emoji":"🍇", "tag":"Fresh",     "description":"Crisp, seedless green grapes with a mild sweet flavour. Rich in antioxidants. Perfect for snacking, salads, or fruit platters."},
    {"id":7,  "name":"Tomatoes",            "cat":"vegetable", "price":39,  "unit":"500 g",   "emoji":"🍅", "tag":"Daily",     "description":"Fresh, firm red tomatoes sourced locally. Versatile kitchen staple — perfect for curries, salads, chutneys, and soups. Rich in lycopene."},
    {"id":8,  "name":"Spinach",             "cat":"vegetable", "price":29,  "unit":"250 g",   "emoji":"🥬", "tag":"Organic",   "description":"Organically grown tender spinach leaves. Iron-rich superfood packed with Vitamins K and A. Perfect for palak dishes, salads, or smoothies."},
    {"id":9,  "name":"Carrots",             "cat":"vegetable", "price":45,  "unit":"500 g",   "emoji":"🥕", "tag":"Fresh",     "description":"Fresh, crunchy carrots rich in beta-carotene and Vitamin A. Great for halwa, soups, stir-fries, or as a healthy raw snack."},
    {"id":10, "name":"Potatoes",            "cat":"vegetable", "price":35,  "unit":"1 kg",    "emoji":"🥔", "tag":"Daily",     "description":"The most versatile vegetable in the kitchen. Firm, starchy potatoes ideal for curries, fries, roasting, or aloo-based dishes."},
    {"id":11, "name":"Broccoli",            "cat":"vegetable", "price":79,  "unit":"1 head",  "emoji":"🥦", "tag":"Fresh",     "description":"A whole fresh head of broccoli. One of the most nutrient-dense vegetables, loaded with Vitamin C, K, and fibre. Great stir-fried or steamed."},
    {"id":12, "name":"Hot Peppers",         "cat":"vegetable", "price":69,  "unit":"3 pcs",   "emoji":"🌶️","tag":"Fresh",     "description":"Fiery red chillies to spice up any dish. High in capsaicin which boosts metabolism. Essential for Indian curries, chutneys, and pickles."},
    {"id":13, "name":"Full Cream Milk",     "cat":"dairy",     "price":64,  "unit":"1 L",     "emoji":"🥛", "tag":"Daily",     "description":"Fresh full-cream pasteurised milk. A daily essential rich in calcium, protein, and Vitamin D. Ideal for drinking, tea, chai, and cooking."},
    {"id":14, "name":"Paneer",              "cat":"dairy",     "price":129, "unit":"200 g",   "emoji":"🧀", "tag":"Fresh",     "description":"Fresh, soft cottage cheese made from pure cow's milk. Protein-rich vegetarian staple. Ideal for palak paneer, paneer tikka, or bhurji."},
    {"id":15, "name":"Curd (Dahi)",         "cat":"dairy",     "price":49,  "unit":"400 g",   "emoji":"🍶", "tag":"Probiotic", "description":"Thick, creamy probiotic curd made from fresh whole milk. Great for gut health. Use in raita, lassi, marinades, or simply with rice."},
    {"id":16, "name":"Butter",              "cat":"dairy",     "price":59,  "unit":"100 g",   "emoji":"🧈", "tag":"Daily",     "description":"Rich and creamy unsalted butter made from fresh cream. Perfect for spreading, baking, and cooking. Adds depth and richness to every dish."},
    {"id":17, "name":"Whole Wheat Bread",   "cat":"bakery",    "price":55,  "unit":"400 g",   "emoji":"🍞", "tag":"Fresh",     "description":"Freshly baked whole wheat bread with soft texture and nutty flavour. High in dietary fibre. Great for sandwiches, toast, or with soups."},
    {"id":18, "name":"Croissants",          "cat":"bakery",    "price":89,  "unit":"4 pcs",   "emoji":"🥐", "tag":"Baked",     "description":"Buttery, flaky croissants baked fresh every morning. Light and airy layers make them perfect for breakfast. Enjoy plain or with jam."},
    {"id":19, "name":"Multigrain Biscuits", "cat":"snacks",    "price":75,  "unit":"200 g",   "emoji":"🍪", "tag":"Healthy",   "description":"Crunchy multigrain biscuits packed with oats, wheat, and seeds. A healthier snacking option with no artificial preservatives. Great with tea."},
    {"id":20, "name":"Potato Chips",        "cat":"snacks",    "price":40,  "unit":"90 g",    "emoji":"🥨", "tag":"Popular",   "description":"Crispy, thin-sliced potato chips lightly salted to perfection. India's favourite snack. Perfect for parties, movie nights, or anytime cravings."},
    {"id":21, "name":"Trail Mix",           "cat":"snacks",    "price":199, "unit":"300 g",   "emoji":"🌰", "tag":"Healthy",   "description":"A nutritious mix of nuts, seeds, and dried fruits. Packed with protein, healthy fats, and natural sugars. The perfect energy-boosting snack."},
    {"id":22, "name":"Orange Juice",        "cat":"beverage",  "price":99,  "unit":"1 L",     "emoji":"🍊", "tag":"Fresh",     "description":"100% freshly squeezed orange juice with no added sugar or preservatives. Rich in Vitamin C and natural antioxidants. A refreshing morning drink."},
    {"id":23, "name":"Green Tea",           "cat":"beverage",  "price":149, "unit":"25 bags", "emoji":"🍵", "tag":"Wellness",  "description":"Premium Darjeeling green tea bags. Rich in catechins and antioxidants that boost metabolism and support immunity. A calming wellness ritual."},
    {"id":24, "name":"Coconut Water",       "cat":"beverage",  "price":69,  "unit":"200 ml",  "emoji":"🥥", "tag":"Natural",   "description":"Pure, natural coconut water from young green coconuts. A natural electrolyte drink that hydrates and replenishes minerals post-workout."},
    {"id":25, "name":"Avocado",             "cat":"vegetable", "price":119, "unit":"3 pcs",   "emoji":"🥑", "tag":"Fresh",     "description":"Creamy, ripe Hass avocados loaded with heart-healthy monounsaturated fats. Rich in Vitamin E and potassium. Great for guacamole or toast."},
]

# ── Page Routes ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if 'user_email' not in session:
        return redirect('/login')
    return send_file("freshmart.html")

@app.route("/login")
def login_page():
    if 'user_email' in session:
        return redirect('/')
    return send_file("login.html")

# ── Auth API ──────────────────────────────────────────────────────────────────
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    name     = data.get('name', '').strip()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')
    if not name or not email or not password:
        return jsonify({"error": "All fields are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (name, email, password_hash) VALUES (?,?,?)",
                     (name, email, generate_password_hash(password)))
        conn.commit()
        session['user_email'] = email
        session['user_name']  = name
        return jsonify({"success": True, "name": name, "email": email})
    except sqlite3.IntegrityError:
        return jsonify({"error": "An account with this email already exists"}), 409
    finally:
        conn.close()

@app.route("/api/login", methods=["POST"])
def login():
    data     = request.json
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({"error": "Invalid email or password"}), 401
    session['user_email'] = email
    session['user_name']  = user['name']
    return jsonify({"success": True, "name": user['name'], "email": email})

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/api/me")
def me():
    if 'user_email' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify({"name": session['user_name'], "email": session['user_email']})

# ── Products API ──────────────────────────────────────────────────────────────
@app.route("/api/products")
def get_products():
    return jsonify(PRODUCTS)

# ── Orders API ────────────────────────────────────────────────────────────────
@app.route("/api/orders")
def get_orders():
    if 'user_email' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM orders WHERE user_email=? ORDER BY placed_at DESC",
        (session['user_email'],)
    ).fetchall()
    conn.close()
    return jsonify([{
        "id": r['id'], "items": json.loads(r['items_json']),
        "subtotal": r['subtotal'], "delivery_fee": r['delivery_fee'],
        "total": r['total'], "item_count": r['item_count'],
        "delivery_address": r['delivery_address'], "placed_at": r['placed_at']
    } for r in rows])

# ── Checkout API ──────────────────────────────────────────────────────────────
@app.route("/api/checkout", methods=["POST"])
def checkout():
    if 'user_email' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    data             = request.json
    cart             = data.get("cart", {})
    delivery_address = data.get("delivery_address", "")
    lat              = data.get("lat")
    lng              = data.get("lng")
    if not cart:
        return jsonify({"error": "Cart is empty"}), 400

    subtotal, item_count, items_detail = 0, 0, []
    for pid_str, qty in cart.items():
        if qty <= 0: continue
        try: pid = int(pid_str)
        except ValueError: continue
        product = next((p for p in PRODUCTS if p["id"] == pid), None)
        if product:
            line = product["price"] * qty
            subtotal    += line
            item_count  += qty
            items_detail.append({"id": product["id"], "name": product["name"],
                                  "emoji": product["emoji"], "price": product["price"],
                                  "unit": product["unit"], "qty": qty, "line_total": line})

    delivery_fee = 0 if subtotal >= 299 else 49
    total = subtotal + delivery_fee

    conn = get_db()
    conn.execute(
        "INSERT INTO orders (user_email,items_json,subtotal,delivery_fee,total,item_count,delivery_address,lat,lng) VALUES (?,?,?,?,?,?,?,?,?)",
        (session['user_email'], json.dumps(items_detail), subtotal, delivery_fee, total, item_count, delivery_address, lat, lng)
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True, "subtotal": subtotal,
                    "delivery_fee": delivery_fee, "total": total, "item_count": item_count})

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
