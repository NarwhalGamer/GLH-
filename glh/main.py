from flask import Flask, render_template, redirect, url_for, session, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from datetime import datetime

# Set up the Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'glh-secret-key-2026'

# Database config — SQLite file will be created automatically
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialise extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Tells Flask-Login how to find a user from their ID stored in the session
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ── DATABASE MODELS ──────────────────────────────────────────

# Users table — stores customers, producers and staff
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    # Password is stored as a hash, never plain text
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer')
    loyalty_points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Producers table — info about each farm/producer
class Producer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(150))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    products = db.relationship('Product', backref='producer', lazy=True)

# Products table — all products listed on the platform
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50))
    allergens = db.Column(db.String(200))  # Required by FSA regulations
    status = db.Column(db.String(20), default='pending')
    producer_id = db.Column(db.Integer, db.ForeignKey('producer.id'), nullable=False)

# Orders table — records every order placed
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_type = db.Column(db.String(20), nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), default='preparing')
    date = db.Column(db.DateTime, default=datetime.utcnow)
    time_slot = db.Column(db.String(20))
    user = db.relationship('User', backref='orders')

# ── ROUTES ───────────────────────────────────────────────────

# Homepage
@app.route('/')
def index():
    producers = Producer.query.limit(3).all()
    return render_template('index.html', producers=producers)

# Products page — shows all live products with optional filtering
@app.route('/products')
def products():
    category = request.args.get('category')
    producer_id = request.args.get('producer')
    max_price = request.args.get('max_price')

    # Start with all live products
    query = Product.query.filter_by(status='live')

    # Apply filters if provided
    if category:
        query = query.filter_by(category=category)
    if producer_id:
        query = query.filter_by(producer_id=producer_id)
    if max_price:
        query = query.filter(Product.price <= float(max_price))

    products = query.all()
    producers = Producer.query.all()
    categories = db.session.query(Product.category).distinct().all()

    return render_template('products.html', products=products,
                           producers=producers, categories=categories)

# Register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name').strip()
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        # Check nothing is empty
        if not name or not email or not password:
            flash('Please fill in all fields.', 'danger')
            return redirect(url_for('register'))

        # Check passwords match
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        # Check email isn't already registered
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with that email already exists.', 'danger')
            return redirect(url_for('register'))

        # Hash the password before saving
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

        new_user = User(name=name, email=email, password=hashed_pw, role='customer')
        db.session.add(new_user)
        db.session.commit()

        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        # Check user exists and password matches the stored hash
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash(f'Welcome back, {user.name}!', 'success')

            # Redirect based on role
            if user.role == 'staff':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'producer':
                return redirect(url_for('producer_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Incorrect email or password.', 'danger')

    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

# Basket page — reads basket from session
@app.route('/basket')
def basket():
    basket_items = session.get('basket', [])
    total = sum(item['price'] * item['quantity'] for item in basket_items)
    return render_template('basket.html', basket_items=basket_items, total=total)

# Add item to basket — stored in session
@app.route('/add_to_basket/<int:product_id>', methods=['POST'])
def add_to_basket(product_id):
    product = Product.query.get_or_404(product_id)
    basket = session.get('basket', [])

    # Check if item already in basket
    for item in basket:
        if item['id'] == product_id:
            item['quantity'] += 1
            session['basket'] = basket
            flash(f'{product.name} quantity updated.', 'success')
            return redirect(url_for('products'))

    # Add new item to basket
    basket.append({
        'id': product_id,
        'name': product.name,
        'price': product.price,
        'quantity': 1
    })
    session['basket'] = basket
    flash(f'{product.name} added to basket!', 'success')
    return redirect(url_for('products'))

# Remove item from basket
@app.route('/remove_from_basket/<int:product_id>')
def remove_from_basket(product_id):
    basket = session.get('basket', [])
    basket = [item for item in basket if item['id'] != product_id]
    session['basket'] = basket
    flash('Item removed from basket.', 'success')
    return redirect(url_for('basket'))

# Place order — saves order to database
@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    basket_items = session.get('basket', [])

    if not basket_items:
        flash('Your basket is empty.', 'danger')
        return redirect(url_for('basket'))

    total = sum(item['price'] * item['quantity'] for item in basket_items)
    order_type = request.form.get('order_type')
    time_slot = request.form.get('time_slot')

    # Save the order to the database
    new_order = Order(
        user_id=current_user.id,
        order_type=order_type,
        total=total + 2.50,
        time_slot=time_slot,
        status='preparing'
    )
    db.session.add(new_order)
    db.session.commit()

    # Clear the basket after order is placed
    session['basket'] = []
    flash('Order placed successfully!', 'success')
    return redirect(url_for('order_confirmation', order_id=new_order.id))

# Order confirmation page
@app.route('/order_confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('order_confirmation.html', order=order)


# Producer dashboard — only accessible to producers
@app.route('/producer/dashboard')
@login_required
def producer_dashboard():
    if current_user.role != 'producer':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    producer = Producer.query.filter_by(user_id=current_user.id).first()
    products = Product.query.filter_by(producer_id=producer.id).all() if producer else []
    orders = Order.query.filter_by(status='preparing').all()
    return render_template('producer_dashboard.html', products=products, orders=orders)


# Add a new product
@app.route('/producer/add_product', methods=['POST'])
@login_required
def add_product():
    if current_user.role != 'producer':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    producer = Producer.query.filter_by(user_id=current_user.id).first()
    name = request.form.get('name')
    description = request.form.get('description')
    price = float(request.form.get('price'))
    stock = int(request.form.get('stock'))
    category = request.form.get('category')
    allergens = request.form.get('allergens')

    # New products go to pending until staff approve them
    new_product = Product(
        name=name,
        description=description,
        price=price,
        stock=stock,
        category=category,
        allergens=allergens,
        status='pending',
        producer_id=producer.id
    )
    db.session.add(new_product)
    db.session.commit()
    flash('Product submitted for approval!', 'success')
    return redirect(url_for('producer_dashboard'))


# Edit a product
@app.route('/producer/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if current_user.role != 'producer':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        product.name = request.form.get('name')
        product.price = float(request.form.get('price'))
        product.stock = int(request.form.get('stock'))
        product.allergens = request.form.get('allergens')
        db.session.commit()
        flash('Product updated!', 'success')
        return redirect(url_for('producer_dashboard'))

    return render_template('edit_product.html', product=product)


# Delete a product
@app.route('/producer/delete_product/<int:product_id>')
@login_required
def delete_product(product_id):
    if current_user.role != 'producer':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product removed.', 'success')
    return redirect(url_for('producer_dashboard'))


# Mark order as ready
@app.route('/producer/mark_ready/<int:order_id>')
@login_required
def mark_order_ready(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = 'ready'
    db.session.commit()
    flash('Order marked as ready!', 'success')
    return redirect(url_for('producer_dashboard'))
# Admin dashboard — only accessible to staff
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'staff':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    pending_products = Product.query.filter_by(status='pending').all()
    orders = Order.query.order_by(Order.date.desc()).all()
    users = User.query.all()
    total_orders = Order.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total)).scalar() or 0
    total_users = User.query.count()
    total_products = Product.query.filter_by(status='live').count()

    return render_template('admin_dashboard.html',
                           pending_products=pending_products,
                           orders=orders,
                           users=users,
                           total_orders=total_orders,
                           total_revenue=total_revenue,
                           total_users=total_users,
                           total_products=total_products)

# Approve a product
@app.route('/admin/approve_product/<int:product_id>')
@login_required
def approve_product(product_id):
    if current_user.role != 'staff':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    product = Product.query.get_or_404(product_id)
    product.status = 'live'
    db.session.commit()
    flash(f'{product.name} approved and is now live!', 'success')
    return redirect(url_for('admin_dashboard'))

# Reject a product
@app.route('/admin/reject_product/<int:product_id>')
@login_required
def reject_product(product_id):
    if current_user.role != 'staff':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash(f'{product.name} rejected and removed.', 'danger')
    return redirect(url_for('admin_dashboard'))

# Update order status
@app.route('/admin/update_order/<int:order_id>')
@login_required
def update_order_status(order_id):
    if current_user.role != 'staff':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    order = Order.query.get_or_404(order_id)
    # Cycle through statuses
    if order.status == 'preparing':
        order.status = 'ready'
    elif order.status == 'ready':
        order.status = 'delivered'
    db.session.commit()
    flash(f'Order #{order.id} status updated to {order.status}.', 'success')
    return redirect(url_for('admin_dashboard'))

# Delete a user
@app.route('/admin/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if current_user.role != 'staff':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User removed.', 'success')
    return redirect(url_for('admin_dashboard'))

# Product detail page
@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product.html', product=product)

# Our Producers page
@app.route('/producers')
def our_producers():
    producers = Producer.query.all()
    return render_template('producers.html', producers=producers)

# About page
@app.route('/about')
def about():
    return render_template('about.html')

# My Account page
@app.route('/account')
@login_required
def account():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date.desc()).all()
    return render_template('account.html', orders=orders)

# ── SAMPLE DATA ───────────────────────────────────────────────

def add_sample_data():
    # Only add sample data if the database is empty
    if Producer.query.first():
        return

    # Create sample producers
    hillside = Producer(name='Hillside Farm', description='A small family farm just outside Greenfield. Free range chickens and seasonal veg, been part of the hub from day one.', location='Greenfield')
    greenway = Producer(name='Greenway Bakery', description='Fresh baked every morning using grain from nearby farms. Run by two people out of a small bakery in the village.', location='Greenfield')
    meadow = Producer(name='Meadow Bees', description='Small beekeeping setup on the outskirts of Greenfield. Raw honey, been growing their hives for a few years now.', location='Greenfield')

    db.session.add_all([hillside, greenway, meadow])
    db.session.commit()

    # Create a producer user account for testing
    hashed_pw = bcrypt.generate_password_hash('producer123').decode('utf-8')
    producer_user = User(name='Hillside Farm', email='hillside@glh.com', password=hashed_pw, role='producer')
    db.session.add(producer_user)
    db.session.commit()

    # Link the producer user to the Hillside Farm producer record
    hillside.user_id = producer_user.id
    db.session.commit()

    # Create a staff account for testing
    hashed_staff_pw = bcrypt.generate_password_hash('staff123').decode('utf-8')
    staff_user = User(name='GLH Staff', email='staff@glh.com', password=hashed_staff_pw, role='staff')
    db.session.add(staff_user)
    db.session.commit()

    # Create sample products
    products = [
        Product(name='Free Range Eggs', description='Our hens roam freely on 40 acres of Greenfield pasture.', price=2.50, stock=48, category='Dairy & Eggs', allergens='Eggs', status='live', producer_id=hillside.id),
        Product(name='Full Fat Milk', description='Fresh whole milk delivered to the hub twice a week.', price=1.20, stock=24, category='Dairy & Eggs', allergens='Milk', status='live', producer_id=hillside.id),
        Product(name='Sourdough Loaf', description='Slow fermented sourdough baked fresh every morning.', price=3.80, stock=10, category='Bakery', allergens='Gluten, Wheat', status='live', producer_id=greenway.id),
        Product(name='Seeded Rolls 6pk', description='Six seeded rolls baked fresh daily.', price=2.20, stock=15, category='Bakery', allergens='Gluten, Wheat, Sesame', status='live', producer_id=greenway.id),
        Product(name='Raw Honey', description='Raw unfiltered honey from our Greenfield hives.', price=4.50, stock=12, category='Honey', allergens='None', status='live', producer_id=meadow.id),
        Product(name='Seasonal Veg Box', description='A mixed box of whatever is in season this week.', price=9.99, stock=8, category='Vegetables', allergens='None', status='live', producer_id=meadow.id),
    ]

    db.session.add_all(products)
    db.session.commit()
    print("Sample data added.")

# ── RUN ──────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        add_sample_data()
        print("Database ready.")
    app.run(debug=True)