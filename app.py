from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import random

app = Flask(__name__)
app.secret_key = 'topuphub_super_secret_key_123'

# Database Setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///topup_hub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ----------------- DATABASE MODELS -----------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    coins = db.Column(db.Integer, default=50)
    last_spin_date = db.Column(db.String(20), nullable=True) # Per day spin track

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_uid = db.Column(db.String(50), nullable=False)
    game_title = db.Column(db.String(50), nullable=False)
    pack_name = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    payment_method = db.Column(db.String(20), default="UPI") 
    status = db.Column(db.String(20), default="Pending")
    user_email = db.Column(db.String(120), nullable=True)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(255), nullable=True)

with app.app_context():
    db.create_all()

# ----------------- ROUTES -----------------

@app.route('/')
def home():
    user_data = None
    if 'user_email' in session:
        user = User.query.filter_by(email=session['user_email']).first()
        if user:
            user_data = {
                'username': user.username,
                'email': user.email,
                'coins': user.coins
            }
    reviews = Review.query.order_by(Review.id.desc()).limit(5).all()
    return render_template('index.html', user=user_data, reviews=reviews)

# Auth
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    existing_user = User.query.filter_by(email=data.get('email')).first()
    if existing_user:
        return jsonify({"status": "error", "message": "यह ईमेल पहले से रजिस्टर्ड है!"})

    new_user = User(username=data.get('username'), email=data.get('email'), password=data.get('password'), coins=50)
    db.session.add(new_user)
    db.session.commit()
    session['user_email'] = new_user.email
    return jsonify({"status": "success", "message": "खाता बन गया! 50 कॉइन्स बोनस मिले 🎉"})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data.get('email'), password=data.get('password')).first()
    if user:
        session['user_email'] = user.email
        return jsonify({"status": "success", "message": "लॉगिन सफल!"})
    return jsonify({"status": "error", "message": "गलत ईमेल या पासवर्ड!"})

@app.route('/logout')
def logout():
    session.pop('user_email', None)
    return redirect(url_for('home'))

# Check Spin Eligibility
@app.route('/api/check-spin-eligibility', methods=['POST'])
def check_spin():
    if 'user_email' not in session:
        return jsonify({"can_spin": True}) # Client handle karega login prompt
    
    user = User.query.filter_by(email=session['user_email']).first()
    today_str = str(date.today())
    
    if user.last_spin_date == today_str:
        return jsonify({"can_spin": False}) # Video Ad dekhna padega
    return jsonify({"can_spin": True})

# Spin Wheel Action
@app.route('/api/spin-wheel', methods=['POST'])
def spin_wheel():
    if 'user_email' not in session:
        return jsonify({"status": "error", "message": "सिक्के जीतने के लिए पहले लॉगिन करें!"})

    user = User.query.filter_by(email=session['user_email']).first()
    
    # Rewards Options
    rewards = [
        {"type": "coins", "val": 10, "text": "आपने 10 सिक्के जीते! 🪙"},
        {"type": "coins", "val": 20, "text": "आपने 20 सिक्के जीते! 🪙"},
        {"type": "coins", "val": 30, "text": "शानदार! आपने 30 सिक्के जीते! 🪙"},
        {"type": "diamond", "val": 1, "text": "🎉 बधाई हो! आपने FREE 1 Diamond जीता!"},
        {"type": "diamond", "val": 5, "text": "🔥 बंपर इनाम! आपने FREE 5 Diamonds जीते!"}
    ]
    
    won = random.choice(rewards)
    
    if won['type'] == 'coins':
        user.coins += won['val']
    else:
        user.coins += (won['val'] * 10) # 1 Diamond = 10 Coins equivalent

    user.last_spin_date = str(date.today())
    db.session.commit()

    return jsonify({"status": "success", "reward_text": won['text'], "new_total": user.coins})

# Watch Ad
@app.route('/api/watch-ad', methods=['POST'])
def watch_ad():
    if 'user_email' not in session:
        return jsonify({"status": "error", "message": "पहले लॉगिन करें!"})

    user = User.query.filter_by(email=session['user_email']).first()
    user.coins += 20
    db.session.commit()
    return jsonify({"status": "success", "reward": 20, "new_total": user.coins})

# Daily Claim
@app.route('/api/daily-claim', methods=['POST'])
def daily_claim():
    if 'user_email' not in session:
        return jsonify({"status": "error", "message": "पहले लॉगिन करें!"})

    user = User.query.filter_by(email=session['user_email']).first()
    user.coins += 30
    db.session.commit()
    return jsonify({"status": "success", "reward": 30, "new_total": user.coins})

# Place Order & Reviews
@app.route('/api/place-order', methods=['POST'])
def place_order():
    data = request.json
    user_email = session.get('user_email', 'Guest')
    pay_method = data.get('payment_method', 'UPI')
    price = int(data['price'])

    if pay_method == 'COINS':
        if 'user_email' not in session:
            return jsonify({"status": "error", "message": "कॉइन्स से खरीदने के लिए लॉगिन ज़रूरी है!"})
        user = User.query.filter_by(email=session['user_email']).first()
        required_coins = price * 10
        if user.coins < required_coins:
            return jsonify({"status": "error", "message": f"अपर्याप्त सिक्के! चाहिए: {required_coins} कॉइन्स।"})
        user.coins -= required_coins
        db.session.commit()

    new_order = Order(player_uid=data['player_uid'], game_title=data['game_title'], pack_name=data['pack_name'], price=price, payment_method=pay_method, status="Pending", user_email=user_email)
    db.session.add(new_order)
    db.session.commit()
    return jsonify({"status": "success", "order_id": new_order.id})

@app.route('/api/submit-review', methods=['POST'])
def submit_review():
    data = request.json
    new_review = Review(username=data.get('username', 'Anonymous Gamer'), rating=int(data.get('rating', 5)), comment=data.get('comment', 'Great App!'))
    db.session.add(new_review)
    if 'user_email' in session:
        user = User.query.filter_by(email=session['user_email']).first()
        if user: user.coins += 10
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/admin-dashboard-secret')
def admin_dashboard():
    orders = Order.query.order_by(Order.id.desc()).all()
    return render_template('admin.html', orders=orders)

if __name__ == '__main__':
    app.run(debug=True)