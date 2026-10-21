from flask import Flask, jsonify, request
from flask_cors import CORS
import pickle
import pandas as pd
from prophet import Prophet
from datetime import datetime
import requests
# import base64

# ─── Import API keys from config.py ───
import os

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SERP_API_KEY = os.environ.get("SERP_API_KEY")
from google import genai
from google.genai import types
import os

SERP_API_KEY = os.environ.get("SERP_API_KEY")

# Initialize the new Gemini SDK
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)


# ═══════════════════════════════════════════════
# UPCOMING SALE — Real 2026 dates + LIVE detection
# ═══════════════════════════════════════════════
def get_upcoming_sale():
    today = datetime.today()

    sales = [
        {"name": "Flipkart Summer Sale",         "date": datetime(2026, 4, 7),   "end": datetime(2026, 4, 20),  "discount": "Up to 80% off"},
        {"name": "IPL Season Sale",               "date": datetime(2026, 4, 15),  "end": datetime(2026, 4, 20),  "discount": "Up to 40% off"},
        {"name": "Amazon Great Summer Sale",      "date": datetime(2026, 5, 1),   "end": datetime(2026, 5, 7),   "discount": "Up to 80% off"},
        {"name": "Myntra End of Season Sale",     "date": datetime(2026, 6, 20),  "end": datetime(2026, 6, 30),  "discount": "Up to 70% off"},
        {"name": "Amazon Prime Day",              "date": datetime(2026, 7, 12),  "end": datetime(2026, 7, 15),  "discount": "Up to 70% off"},
        {"name": "Flipkart GOAT Sale",            "date": datetime(2026, 7, 12),  "end": datetime(2026, 7, 15),  "discount": "Up to 75% off"},
        {"name": "Amazon Great Freedom Sale",     "date": datetime(2026, 8, 1),   "end": datetime(2026, 8, 5),   "discount": "Up to 70% off"},
        {"name": "Independence Day Sale",         "date": datetime(2026, 8, 15),  "end": datetime(2026, 8, 17),  "discount": "Up to 50% off"},
        {"name": "Amazon Great Indian Festival",  "date": datetime(2026, 9, 23),  "end": datetime(2026, 10, 5),  "discount": "Up to 90% off"},
        {"name": "Flipkart Big Billion Days",     "date": datetime(2026, 9, 30),  "end": datetime(2026, 10, 4),  "discount": "Up to 80% off"},
        {"name": "Myntra Big Fashion Festival",   "date": datetime(2026, 10, 8),  "end": datetime(2026, 10, 14), "discount": "Up to 80% off"},
        {"name": "Diwali Mega Sale",              "date": datetime(2026, 10, 15), "end": datetime(2026, 10, 22), "discount": "Up to 70% off"},
        {"name": "Black Friday Sale",             "date": datetime(2026, 11, 20), "end": datetime(2026, 11, 30), "discount": "Up to 60% off"},
        {"name": "Flipkart Christmas Sale",       "date": datetime(2026, 12, 22), "end": datetime(2026, 12, 28), "discount": "Up to 50% off"},
        {"name": "Amazon Year-End Sale",          "date": datetime(2026, 12, 25), "end": datetime(2026, 12, 31), "discount": "Up to 55% off"},
    ]

    # ── Check if a sale is currently LIVE ──
    live = [s for s in sales if s["date"] <= today <= s["end"]]
    if live:
        s = live[0]
        days_left = (s["end"] - today).days
        return {
            "name":     s["name"],
            "date":     s["date"].strftime("%d %B %Y"),
            "end_date": s["end"].strftime("%d %B %Y"),
            "days_left": days_left,
            "discount": s["discount"],
            "status":   "LIVE"
        }

    # ── Otherwise return the next upcoming sale ──
    upcoming = [s for s in sales if s["date"] > today]
    upcoming.sort(key=lambda x: x["date"])

    if not upcoming:
        return {
            "name":     "Sale Coming Soon",
            "date":     "TBA",
            "end_date": "TBA",
            "days_left": 0,
            "discount": "Stay tuned",
            "status":   "upcoming"
        }

    s = upcoming[0]
    days_left = (s["date"] - today).days
    return {
        "name":     s["name"],
        "date":     s["date"].strftime("%d %B %Y"),
        "end_date": s["end"].strftime("%d %B %Y"),
        "days_left": days_left,
        "discount": s["discount"],
        "status":   "upcoming"
    }


# ═══════════════════════════════════════════════
# BANK OFFERS DATA
# ═══════════════════════════════════════════════
bank_offers = [
    {"bank": "HDFC",   "offer": "10% cashback",      "max": "upto ₹500",         "code": "HDFC10"},
    {"bank": "SBI",    "offer": "5% off on EMI",      "max": "upto ₹300",         "code": "SBI5EMI"},
    {"bank": "ICICI",  "offer": "₹200 instant off",   "max": "on orders ₹1500+",  "code": "ICICI200"},
    {"bank": "AXIS",   "offer": "15% cashback",       "max": "upto ₹400",         "code": "AXIS15"},
    {"bank": "KOTAK",  "offer": "₹150 instant off",   "max": "on all orders",     "code": "KOTAK150"},
    {"bank": "IDFC",   "offer": "20% off",            "max": "upto ₹600",         "code": "IDFC20"},
]


# ═══════════════════════════════════════════════
# PLATFORM PRICES WITH DIRECT BUY LINKS
# ═══════════════════════════════════════════════
platform_prices = {

    "boat": [
        {
            "platform": "Amazon",   "price": 1799,  "original": 2999,
            "discount": "10% off",  "delivery": "Free, Tomorrow",
            "link": "https://www.amazon.in/s?k=boat+rockerz+450",
            "lowest": True,         "color": "#FF9900"
        },
        {
            "platform": "Flipkart", "price": 1849,  "original": 2999,
            "discount": "5% off",   "delivery": "Free, 2 days",
            "link": "https://www.flipkart.com/search?q=boat+rockerz+450",
            "lowest": False,        "color": "#2874F0"
        },
        {
            "platform": "Meesho",   "price": 1299,  "original": 1999,
            "discount": "No offers","delivery": "₹50, 5 days",
            "link": "https://www.meesho.com/search?q=boat+rockerz+450",
            "lowest": False,        "color": "#F43397"
        },
        {
            "platform": "Snapdeal", "price": 1699,  "original": 2499,
            "discount": "8% off",   "delivery": "Free, 3 days",
            "link": "https://www.snapdeal.com/search?keyword=boat+rockerz+450",
            "lowest": False,        "color": "#E40000"
        },
        {
            "platform": "Myntra",   "price": 1999,  "original": 2999,
            "discount": "No offers","delivery": "Free, 2 days",
            "link": "https://www.myntra.com/boat+rockerz+450",
            "lowest": False,        "color": "#FF3F6C"
        },
        {
            "platform": "Ajio",     "price": 1749,  "original": 2499,
            "discount": "5% off",   "delivery": "Free, 3 days",
            "link": "https://www.ajio.com/search/?text=boat+rockerz+450",
            "lowest": False,        "color": "#8B5CF6"
        },
    ],

    "nike": [
        {
            "platform": "Amazon",   "price": 4995,  "original": 7999,
            "discount": "8% off",   "delivery": "Free, Tomorrow",
            "link": "https://www.amazon.in/s?k=nike+revolution+6",
            "lowest": False,        "color": "#FF9900"
        },
        {
            "platform": "Flipkart", "price": 4799,  "original": 7999,
            "discount": "10% off",  "delivery": "Free, 2 days",
            "link": "https://www.flipkart.com/search?q=nike+revolution+6",
            "lowest": True,         "color": "#2874F0"
        },
        {
            "platform": "Myntra",   "price": 5195,  "original": 7999,
            "discount": "5% off",   "delivery": "Free, 2 days",
            "link": "https://www.myntra.com/nike+revolution+6",
            "lowest": False,        "color": "#FF3F6C"
        },
        {
            "platform": "Ajio",     "price": 4999,  "original": 7999,
            "discount": "7% off",   "delivery": "Free, 3 days",
            "link": "https://www.ajio.com/search/?text=nike+revolution+6",
            "lowest": False,        "color": "#8B5CF6"
        },
        {
            "platform": "Snapdeal", "price": 5299,  "original": 7999,
            "discount": "3% off",   "delivery": "Free, 4 days",
            "link": "https://www.snapdeal.com/search?keyword=nike+revolution+6",
            "lowest": False,        "color": "#E40000"
        },
        {
            "platform": "Meesho",   "price": 3999,  "original": 5999,
            "discount": "No offers","delivery": "₹50, 6 days",
            "link": "https://www.meesho.com/search?q=nike+revolution+6",
            "lowest": False,        "color": "#F43397"
        },
    ],

    "iphone": [
        {
            "platform": "Amazon",   "price": 69999, "original": 79900,
            "discount": "5% off",   "delivery": "Free, Tomorrow",
            "link": "https://www.amazon.in/s?k=iphone+15+128gb",
            "lowest": False,        "color": "#FF9900"
        },
        {
            "platform": "Flipkart", "price": 68999, "original": 79900,
            "discount": "8% off",   "delivery": "Free, 2 days",
            "link": "https://www.flipkart.com/search?q=iphone+15+128gb",
            "lowest": True,         "color": "#2874F0"
        },
        {
            "platform": "Myntra",   "price": 71999, "original": 79900,
            "discount": "3% off",   "delivery": "Free, 3 days",
            "link": "https://www.myntra.com/iphone+15",
            "lowest": False,        "color": "#FF3F6C"
        },
        {
            "platform": "Snapdeal", "price": 72999, "original": 79900,
            "discount": "2% off",   "delivery": "Free, 4 days",
            "link": "https://www.snapdeal.com/search?keyword=iphone+15",
            "lowest": False,        "color": "#E40000"
        },
        {
            "platform": "Ajio",     "price": 70999, "original": 79900,
            "discount": "4% off",   "delivery": "Free, 3 days",
            "link": "https://www.ajio.com/search/?text=iphone+15",
            "lowest": False,        "color": "#8B5CF6"
        },
        {
            "platform": "Meesho",   "price": 67999, "original": 79900,
            "discount": "No offers","delivery": "₹100, 7 days",
            "link": "https://www.meesho.com/search?q=iphone+15",
            "lowest": False,        "color": "#F43397"
        },
    ],
}


# ═══════════════════════════════════════════════
# ALTERNATIVES DATA
# ═══════════════════════════════════════════════
alternatives = {

    "boat": {
        "budget": [
            {"name": "Zebronics Zeb-Duke1",  "price": 799,  "similarity": "89%", "rating": "3.8", "platform": "Amazon",   "link": "https://www.amazon.in/s?k=zebronics+zeb+duke1"},
            {"name": "PTron Bassbuds Pro",   "price": 599,  "similarity": "85%", "rating": "3.6", "platform": "Meesho",   "link": "https://www.meesho.com/search?q=ptron+bassbuds"},
        ],
        "mid": [
            {"name": "JBL Tune 510BT",       "price": 1299, "similarity": "94%", "rating": "4.2", "platform": "Amazon",   "link": "https://www.amazon.in/s?k=jbl+tune+510bt"},
            {"name": "Noise Shots X5 Pro",   "price": 999,  "similarity": "91%", "rating": "4.0", "platform": "Flipkart", "link": "https://www.flipkart.com/search?q=noise+shots+x5"},
        ],
        "value": [
            {"name": "Sony WH-CH510",        "price": 2990, "similarity": "96%", "rating": "4.4", "platform": "Amazon",   "link": "https://www.amazon.in/s?k=sony+wh+ch510"},
            {"name": "Oneplus Bullets Z2",   "price": 1799, "similarity": "93%", "rating": "4.3", "platform": "Flipkart", "link": "https://www.flipkart.com/search?q=oneplus+bullets+z2"},
        ],
    },

    "nike": {
        "budget": [
            {"name": "Campus OG Running",    "price": 1299, "similarity": "88%", "rating": "4.0", "platform": "Amazon",   "link": "https://www.amazon.in/s?k=campus+og"},
            {"name": "Sparx Running Shoes",  "price": 799,  "similarity": "82%", "rating": "3.7", "platform": "Flipkart", "link": "https://www.flipkart.com/search?q=sparx+running+shoes"},
        ],
        "mid": [
            {"name": "Puma Softride Enzo",   "price": 2499, "similarity": "93%", "rating": "4.3", "platform": "Amazon",   "link": "https://www.amazon.in/s?k=puma+softride"},
            {"name": "Adidas Lite Racer 3",  "price": 3499, "similarity": "95%", "rating": "4.4", "platform": "Myntra",   "link": "https://www.myntra.com/adidas+lite+racer"},
        ],
        "value": [
            {"name": "New Balance Fresh Foam","price": 4499, "similarity": "97%", "rating": "4.5", "platform": "Amazon",   "link": "https://www.amazon.in/s?k=new+balance+fresh+foam"},
            {"name": "Reebok Floatride Run", "price": 3999, "similarity": "94%", "rating": "4.3", "platform": "Ajio",     "link": "https://www.ajio.com/search/?text=reebok+floatride"},
        ],
    },

    "iphone": {
        "budget": [
            {"name": "Poco X6 Pro 5G",       "price": 22999,"similarity": "80%", "rating": "4.2", "platform": "Flipkart", "link": "https://www.flipkart.com/search?q=poco+x6+pro"},
            {"name": "Redmi Note 13 Pro+",   "price": 19999,"similarity": "78%", "rating": "4.1", "platform": "Amazon",   "link": "https://www.amazon.in/s?k=redmi+note+13+pro"},
        ],
        "mid": [
            {"name": "OnePlus 12R 5G",       "price": 39999,"similarity": "90%", "rating": "4.4", "platform": "Amazon",   "link": "https://www.amazon.in/s?k=oneplus+12r"},
            {"name": "Samsung Galaxy A55",   "price": 34999,"similarity": "88%", "rating": "4.3", "platform": "Flipkart", "link": "https://www.flipkart.com/search?q=samsung+galaxy+a55"},
        ],
        "value": [
            {"name": "Samsung Galaxy S23",   "price": 54999,"similarity": "95%", "rating": "4.6", "platform": "Amazon",   "link": "https://www.amazon.in/s?k=samsung+galaxy+s23"},
            {"name": "Google Pixel 8a",      "price": 52999,"similarity": "93%", "rating": "4.5", "platform": "Flipkart", "link": "https://www.flipkart.com/search?q=google+pixel+8a"},
        ],
    },
}


# ═══════════════════════════════════════════════
# ROUTE 1 — SEARCH PRODUCT
# ═══════════════════════════════════════════════
@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('product', '').lower()

    matched = None
    for key in platform_prices:
        if key in query:
            matched = key
            break

    if not matched:
        return jsonify({"error": "Product not found. Try: boat, nike or iphone"}), 404

    platforms = platform_prices[matched]
    lowest = min(platforms, key=lambda x: x["price"])

    return jsonify({
        "key":              matched,
        "platforms":        platforms,
        "lowest_platform":  lowest["platform"],
        "lowest_price":     lowest["price"],
        "bank_offers":      bank_offers,
        "upcoming_sale":    get_upcoming_sale()
    })


# ═══════════════════════════════════════════════
# ROUTE 2 — PRICE PREDICTION (Uses trained model)
# ═══════════════════════════════════════════════
@app.route('/predict', methods=['GET'])
def predict():
    product_key = request.args.get('product', '').lower()

    model_files = {
        "boat":   "boat_model.pkl",
        "nike":   "nike_model.pkl",
        "iphone": "iphone_model.pkl"
    }

    if product_key not in model_files:
        return jsonify({"error": "Product not found. Try: boat, nike or iphone"}), 404

    try:
        with open(model_files[product_key], 'rb') as f:
            model = pickle.load(f)

        future = model.make_future_dataframe(periods=30)
        forecast = model.predict(future)

        platforms     = platform_prices[product_key]
        current_price = min(p["price"] for p in platforms)
        predicted_price = round(forecast['yhat'].iloc[-1])
        lower_bound   = round(forecast['yhat_lower'].iloc[-1])
        upcoming      = get_upcoming_sale()

        if predicted_price < current_price:
            recommendation = "WAIT"
            savings        = current_price - predicted_price
            message        = f"Price expected to drop by ₹{savings:,} in next 30 days. Wait for better deal."
        else:
            recommendation = "BUY NOW"
            savings        = 0
            message        = "Price is at its lowest right now. Great time to buy!"

        return jsonify({
            "product":          product_key,
            "current_price":    current_price,
            "predicted_price":  predicted_price,
            "lower_bound":      lower_bound,
            "recommendation":   recommendation,
            "expected_savings": savings,
            "message":          message,
            "upcoming_sale":    upcoming,
            "days":             14
        })

    except FileNotFoundError:
        return jsonify({"error": f"Model not found. Run train.py first."}), 500


# ═══════════════════════════════════════════════
# ROUTE 3 — ALTERNATIVES
# ═══════════════════════════════════════════════
@app.route('/alternatives', methods=['GET'])
def get_alternatives():
    product_key = request.args.get('product', '').lower()

    if product_key not in alternatives:
        return jsonify({"error": "Product not found"}), 404

    return jsonify(alternatives[product_key])


# ═══════════════════════════════════════════════
# ROUTE 4 — BANK OFFERS
# ═══════════════════════════════════════════════
@app.route('/offers', methods=['GET'])
def get_offers():
    return jsonify({"bank_offers": bank_offers})


# ═══════════════════════════════════════════════
# ROUTE 5 — UPCOMING SALE
# ═══════════════════════════════════════════════
@app.route('/sale', methods=['GET'])
def get_sale():
    return jsonify(get_upcoming_sale())



# ═══════════════════════════════════════════════
# ROUTE 6 — GEMINI VISION: Detect product from image
# ═══════════════════════════════════════════════
@app.route('/detect', methods=['POST'])
def detect_product():
    if 'image' not in request.files:
        return jsonify({
            "error": "No image uploaded. Send image as form-data with key 'image'"
        }), 400

    try:
        image_file = request.files['image']
        image_data = image_file.read()
        mime_type = image_file.content_type or 'image/jpeg'

        prompt = (
            "Look at this image carefully. "
            "What exact product is shown? "
            "Give me ONLY the product brand and model name, nothing else. "
            "Example outputs: 'Nike Air Max 270', "
            "'boAt Rockerz 450', or 'iPhone 15 128GB'. "
            "If you cannot identify a product, say 'Unknown Product'."
        )

        if client is None:
            return jsonify({
                "error": "Gemini feature is unavailable because no Gemini API key is configured."
            }), 503

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=[
                types.Part.from_bytes(
                    data=image_data,
                    mime_type=mime_type
                ),
                prompt
            ]
        )

        product_name = (response.text or "").strip()

        matched = None
        for key in platform_prices:
            if key in product_name.lower():
                matched = key
                break

        return jsonify({
            "detected_product": product_name,
            "matched_key": matched,
            "status": "success"
        })

    except Exception as e:
        app.logger.exception("Product image detection failed")
        return jsonify({"error": str(e)}), 500

# ROUTE 7 — SERPAPI: Live prices from Google Shopping
@app.route('/liveprices', methods=['GET'])
def live_prices():
    product = request.args.get('product', '').strip()

    if not product:
        return jsonify({
            "error": "Send product name as ?product="
        }), 400

    try:
        url = "https://serpapi.com/search"

        params = {
            "engine": "google_shopping",
            "q": product + " India",
            "location": "India",
            "gl": "in",
            "hl": "en",
            "api_key": SERP_API_KEY
        }

        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        response.raise_for_status()
        data = response.json()

        # Handle errors returned by SerpAPI
        if data.get("error"):
            return jsonify({
                "product": product,
                "live_results": [],
                "error": data["error"]
            }), 502

        results = []

        for item in data.get("shopping_results", [])[:6]:
            
            # Use the available product URL, including Google Shopping URLs.
            product_link = (
            item.get("product_link")
            or item.get("link")
            or item.get("product_page_url")
            )


            results.append({
                "platform": item.get("source"),
                "title": item.get("title"),
                "price": item.get("price"),
                "link": product_link,
                "image": item.get("thumbnail"),
                "rating": item.get("rating"),
                "reviews": item.get("reviews")
            })

        return jsonify({
            "product": product,
            "live_results": results,
            "result_count": len(results),
            "source": "SerpAPI Google Shopping"
        })

    except requests.exceptions.Timeout:
        return jsonify({
            "error": "SerpAPI request timed out. Please try again."
        }), 504

    except requests.exceptions.RequestException as e:
        app.logger.error("SerpAPI request failed: %s", e)
        return jsonify({
            "error": "Unable to retrieve live prices from SerpAPI."
        }), 502

    except Exception:
        app.logger.exception("Live price lookup failed")
        return jsonify({
            "error": "An unexpected error occurred while retrieving prices."
        }), 500

# ═══════════════════════════════════════════════
# ROUTE 8 — SERPAPI: Live alternatives
# ═══════════════════════════════════════════════
@app.route('/livealternatives', methods=['GET'])
def live_alternatives():
    product = request.args.get('product', '')
    budget  = request.args.get('budget', '2000')

    if not product:
        return jsonify({"error": "Send product name as ?product="}), 400

    try:
        url = "https://serpapi.com/search"
        params = {
            "engine":   "google_shopping",
            "q":        f"similar to {product} under {budget} rupees India",
            "location": "India",
            "gl":       "in",
            "hl":       "en",
            "api_key":  SERP_API_KEY
        }

        response = requests.get(url, params=params, timeout=10)
        data     = response.json()

        results = []
        for item in data.get("shopping_results", [])[:4]:
            results.append({
                "name":     item.get("title"),
                "price":    item.get("price"),
                "link":     item.get("link"),
                "image":    item.get("thumbnail"),
                "platform": item.get("source")
            })

        return jsonify({"alternatives": results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════
@app.route('/', methods=['GET'])
def health():
    return jsonify({
        "status":  "SmartBuy Planner API is running ✅",
        "routes": [
            "GET  /search?product=boat",
            "GET  /predict?product=boat",
            "GET  /alternatives?product=boat",
            "GET  /offers",
            "GET  /sale",
            "GET  /liveprices?product=nike+shoes",
            "GET  /livealternatives?product=nike&budget=2000",
            "POST /detect  (image file as form-data)"
        ]
    })


# ═══════════════════════════════════════════════
# ROUTE 9 — REAL SEARCH (SerpAPI Google Shopping)
# ═══════════════════════════════════════════════
@app.route('/realsearch', methods=['GET'])
def real_search():
    product = request.args.get('product', '')

    url = "https://serpapi.com/search"
    params = {
        "engine": "google_shopping",
        "q": product,
        "location": "India",
        "gl": "in",
        "hl": "en",
        "num": "10",
        "api_key": SERP_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        results = []
        for item in data.get("shopping_results", [])[:8]:
            results.append({
                "name":     item.get("title"),
                "platform": item.get("source"),
                "price":    item.get("price"),
                "link":     item.get("link"),
                "image":    item.get("thumbnail"),
                "rating":   item.get("rating"),
                "reviews":  item.get("reviews"),
                "lowest":   False
            })

        # Mark lowest price
        if results:
            min_price = min(
                (r for r in results if r["price"] and "₹" in str(r["price"])),
                key=lambda x: float(
                    str(x["price"]).replace("₹", "").replace(",", "").strip()
                )
            )
            min_price["lowest"] = True

        return jsonify({
            "product":      product,
            "results":      results,
            "upcoming_sale": get_upcoming_sale(),
            "bank_offers":  bank_offers
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════
if __name__ == '__main__':
    print("\n🚀 SmartBuy Planner Backend Starting...")
    print("📡 Running on http://127.0.0.1:5000")
    print("🔍 Test: http://127.0.0.1:5000/search?product=boat\n")
    app.run(debug=True, port=5000)