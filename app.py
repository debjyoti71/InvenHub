from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify
from sqlalchemy import func , or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import random
from dotenv import load_dotenv
import os
import time
from config import Config  # Import your Config class
from models import db, User, Store, Product, UserStore, Category, Transaction ,TransactionItem
import csv 
from datetime import datetime ,timedelta
from flask_migrate import Migrate
import uuid

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Use Config class for configuration
app.config.from_object(Config)
# Initialize the database and mail
db.init_app(app)
mail = Mail(app)

with app.app_context():
    db.create_all()

migrate = Migrate(app, db)    

import psycopg2

def calculate_database_size():
    # PostgreSQL connection parameters
    database_url = os.getenv('DATABASE_URL')
    db_url = database_url = os.getenv('DATABASE_URL')

    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        # Query to get the size of the current database
        query = "SELECT pg_size_pretty(pg_database_size(current_database()));"
        cursor.execute(query)

        # Fetch the result
        db_size = cursor.fetchone()[0]  # Get the size in a human-readable format (e.g., '25 MB')
        print(f"Database size: {db_size}")

        # Close the connection
        cursor.close()
        conn.close()

        return db_size
    except Exception as e:
        print(f"Error while calculating database size: {e}")
        return None    

# Route for home page
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/7006')
def config():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    email = session['email']
    user = User.query.filter_by(email=email).first()

    if user.role_name.lower() != 'user':
        secret_key = os.getenv('SECRET_KEY')
        database_url = os.getenv('DATABASE_URL')
        mail_username = os.getenv('MAIL_USERNAME')
        mail_password = os.getenv('MAIL_PASSWORD')
        allowed_user = os.getenv('ALLOWED_USER')
        predefined_password = os.getenv('PREDEFINED_PASSWORD')
        
        return f"""
            <h1>Environment Variables</h1>
            <ul>
                <li><strong>SECRET_KEY:</strong> {secret_key}</li>
                <li><strong>DATABASE_URL:</strong> {database_url}</li>
                <li><strong>MAIL_USERNAME:</strong> {mail_username}</li>
                <li><strong>MAIL_PASSWORD:</strong> {mail_password}</li>
                <li><strong>ALLOWED_USER:</strong> {allowed_user}</li>
                <li><strong>PREDEFINED_PASSWORD:</strong> {predefined_password}</li>
            </ul>
        """
    else:
        return "You are not authorized to view this page.", 403

# Helper functions for authentication
def check_admin(email, password):
    return email == app.config['ALLOWED_USER'] and password == app.config['PREDEFINED_PASSWORD']

def authenticate_user(email, password):
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        return user
    return None


# Handle signup form submission
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm-password']

        # Check if passwords match
        if password != confirm_password:
            return "Passwords do not match!", 400

        # Temporarily store the user data in the session
        session['temp_user'] = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'password': password
        }

        # Generate OTP and send it
        return redirect(url_for('send_otp'))
    
    return render_template('signup.html')

# Send OTP to User Email
@app.route('/send_otp', methods=['GET', 'POST'])
def send_otp():
    user_data = session.get('temp_user')
    if not user_data:
        return redirect(url_for('signup'))  # Redirect to signup if no temp user data

    email = user_data['email']
    
    # Generate a random 6-digit OTP
    otp = random.randint(100000, 999999)
    session['otp'] = otp  # Store OTP in session

    # Send OTP to user’s email
    msg = Message(
        'Your One-Time Password (OTP)', 
        sender=app.config['MAIL_USERNAME'], 
        recipients=[email]
    )
    msg.html = render_template('otpMail_template.html', otp=otp)

    mail.send(msg)

    return redirect(url_for('verify_otp'))

# Verify OTP
@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        otp = ''.join([request.form[f'otp{i}'] for i in range(1, 7)])  # Combine OTP digits

        # Check if the entered OTP matches the one in session
        if 'otp' in session and otp == str(session['otp']):
            session.pop('otp', None)  # Clear OTP after successful verification

            # Save user's data to the database after OTP verification
            user_data = session.pop('temp_user', None)
            if user_data:
                hashed_password = generate_password_hash(user_data['password'])
                new_user = User(
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    email=user_data['email'],
                    phone=user_data['phone'],
                    password=hashed_password
                )

                try:
                    db.session.add(new_user)
                    db.session.commit()
                    session['user'] = user_data['first_name']
                    session['email'] = user_data['email']
                    return redirect(url_for('add_store_form'))

                except IntegrityError:
                    db.session.rollback()
                    return "Email already exists!", 400
            else:
                return "Invalid user data.", 400
        else:
            return "Invalid OTP. Please try again.", 400

    return render_template('otp_verification.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check for the predefined admin credentials
        if email == app.config['ALLOWED_USER'] and password == app.config['PREDEFINED_PASSWORD']:
            session['user'] = 'Admin'  # Store 'Admin' as the display name for admin
            session['email'] = app.config['ALLOWED_USER']  # Store admin email in session
            return redirect(url_for('dashboard'))

        # Check if the user exists in the database
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):  # Check the hashed password
                session['user'] = user.first_name  # Store the first name in the session
                session['email'] = user.email  # Store the user's email in the session

                # Check if the user has an associated store
                if not user.stores:  # Check if the user has no stores associated
                    return redirect(url_for('add_store_form'))  # Redirect to store addition form
                else:
                    return redirect(url_for('dashboard'))  # Redirect to dashboard if store exists
            else:
                return 'Incorrect password, try again.'
        else:
            return 'Email does not exist.'

    return render_template('login.html')

# Forgot Password Route - Request OTP
@app.route('/forget-password', methods=['GET', 'POST'])
def forget_password():
    if request.method == 'GET':
        return render_template('forget_password.html')  # Form to input email

    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()

        if not user:
            flash('Email not found in our records.', 'danger')
            return redirect(url_for('forget_password'))

        otp = random.randint(100000, 999999)
        session['otp'] = otp  # Store OTP in session
        session['email'] = email  # Store email for verification
        session['otp_timestamp'] = time.time()  # Store OTP timestamp to handle expiration

        # Send OTP to user's email
        msg = Message(
            'Your One-Time Password (OTP)',
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.html = render_template('otpMail_template.html', otp=otp)

        try:
            mail.send(msg)
            flash('OTP sent to your email.', 'success')
        except Exception:
            flash('Failed to send OTP. Please try again.', 'danger')
            return redirect(url_for('forget_password'))

        return redirect(url_for('fpverify_otp'))


# Step 2: Verify OTP for Password Reset
@app.route('/forget-password-verify-otp', methods=['GET', 'POST'])
def fpverify_otp():
    if request.method == 'GET':
        return render_template('otp_verification.html')  # Form to input OTP

    if request.method == 'POST':
        entered_otp = request.form['otp']
        stored_otp = session.get('otp')
        email = session.get('email')
        otp_timestamp = session.get('otp_timestamp')

        if not stored_otp or not email or not otp_timestamp:
            flash('Session expired or invalid.', 'danger')
            return redirect(url_for('forget_password'))

        # Check if OTP expired (e.g., after 10 minutes)
        if time.time() - otp_timestamp > 600:  # 10 minutes
            flash('OTP expired. Please request a new one.', 'danger')
            session.pop('otp', None)
            session.pop('otp_timestamp', None)
            return redirect(url_for('forget_password'))

        if str(entered_otp) == str(stored_otp):
            session.pop('otp', None)  # Remove OTP after verification
            flash('OTP verified successfully.', 'success')
            return redirect(url_for('reset_password'))

        flash('Invalid OTP. Please try again.', 'danger')
        return redirect(url_for('fpverify_otp'))


# Step 3: Reset Password
@app.route('/forget-password-reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'GET':
        return render_template('forget-password-reset_password.html')  # Form to input new password

    if request.method == 'POST':
        new_password = request.form['password']
        email = session.get('email')

        if not email:
            flash('Session expired. Please restart the process.', 'danger')
            return redirect(url_for('forget_password'))

        if len(new_password) < 6:  # Ensure a minimum length for password
            flash('Password must be at least 6 characters long.', 'danger')
            return redirect(url_for('reset_password'))

        # Hash the password before saving it
        hashed_password = generate_password_hash(new_password)

        user = User.query.filter_by(email=email).first()
        if user:
            user.password = hashed_password  # Use hashed passwords for security
            db.session.commit()

            session.pop('email', None)  # Clear email from session
            flash('Password reset successfully. You can now log in.', 'success')
            return redirect(url_for('login'))

        flash('User not found. Please restart the process.', 'danger')
        return redirect(url_for('forget_password'))

# Dashboard (only accessible to logged-in users)
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'GET':
        # Fetch the current user based on session
        email = session.get('email')
        if not email:
            flash("User not logged in. Please log in first.", "danger")
            return redirect(url_for('login'))

        current_user = User.query.filter_by(email=email).first()
        if not current_user:
            flash("User not found. Please log in again.", "danger")
            return redirect(url_for('login'))

        # Fetch the user's associated store
        user_store = UserStore.query.filter_by(user_id=current_user.id).first()
        if not user_store:
            flash("No store associated with this user. Please join or create a store first.", "danger")
            return redirect(url_for('add_store_form'))

        store_id = user_store.store_id

        # Fetch and aggregate transactions at the database level
        transactions_summary = (
            db.session.query(
                func.date_trunc('month', Transaction.transaction_date).label('month'),
                func.sum(Transaction.total_cost_price).label('total_cost_price'),
                func.sum(Transaction.total_selling_price).label('total_selling_price')
            )
            .filter_by(store_id=store_id)
            .group_by(func.date_trunc('month', Transaction.transaction_date))
            .all()
        )

        # Convert the aggregated data to a dictionary
        monthly_data = {
            record.month.strftime("%Y-%m"): {
                "cost_price": record.total_cost_price or 0,
                "selling_price": record.total_selling_price or 0
            }
            for record in transactions_summary
        }

        # Fetch daily transactions (if needed)
        daily_transactions_summary = (
            db.session.query(
                func.date_trunc('day', Transaction.transaction_date).label('day'),
                func.sum(Transaction.total_cost_price).label('total_cost_price'),
                func.sum(Transaction.total_selling_price).label('total_selling_price')
            )
            .filter_by(store_id=store_id)
            .group_by(func.date_trunc('day', Transaction.transaction_date))
            .all()
        )

        daily_data = {
            record.day.strftime("%Y-%m-%d"): {
                "cost_price": record.total_cost_price or 0,
                "selling_price": record.total_selling_price or 0
            }
            for record in daily_transactions_summary
        }

        # Fetch products and low stock data
        products = Product.query.join(Category).filter(Category.store_id == store_id).all()
        low_stock_data = {}
        total_stock = 0
        for product in products:
            total_stock += product.stock
            if product.stock <= product.low_stock:
                low_stock_data[product.name] = product.stock

        # Sort low stock data
        low_stock_data = dict(sorted(low_stock_data.items(), key=lambda item: item[1]))

        # Render the dashboard
        return render_template(
            'dashboard.html',
            daily_data=daily_data,
            monthly_data=monthly_data,
            low_stock_data=low_stock_data,
            total_stock=total_stock,
        )

@app.route('/add_store', methods=['GET'])
def add_store_form():
    return render_template('add_store.html')  # HTML file for the add store form

@app.route('/add_store', methods=['POST'])
def add_store():
    # Debugging: print form data
    print("Form data received:", request.form)

    # Get form data
    store_name = request.form.get('store_name')
    store_address = request.form.get('store_address')
    owner_name = request.form.get('owner_name')
    gstNumber = request.form.get('gstNumber')
    business_email = request.form.get('business_email')

    # Debugging: print individual form fields
    print("Store Name:", store_name)
    print("Store Address:", store_address)
    print("Owner Name:", owner_name)
    print("GST Number:", gstNumber)
    print("Business Email:", business_email)

    # Check if all fields are provided
    if store_name and store_address and owner_name and gstNumber and business_email:
        try:
            # Create new store
            new_store = Store(
                store_name=store_name,
                store_address=store_address,
                owner_name=owner_name,
                gstNumber=gstNumber,
                business_email=business_email
            )

            # Debugging: print the store object to verify its creation
            print("New Store Object Created:", new_store)

            # Add the new store to the session
            db.session.add(new_store)

            # Debugging: Check if store is in the session
            print("Store added to session:", new_store in db.session)

            db.session.commit()  # Commit the new store to the database

            # Debugging: Print all stores to verify if it was saved
            all_stores = Store.query.all()
            print("All Stores in DB:", all_stores)

            # Assuming the current user is logged in, associate the store with the logged-in user
            current_user = User.query.filter_by(email=session.get('email')).first()  # Get the current logged-in user
            if current_user:
                print("Current User Found:", current_user)

                # Check if there is already an association between user and store
                association = db.session.query(UserStore).filter_by(user_id=current_user.id, store_id=new_store.id).first()
                if not association:  # Only create the association if it does not exist
                    # Create association between the user and the store
                    new_association = UserStore(user_id=current_user.id, store_id=new_store.id, role_name="Owner")
                    db.session.add(new_association)  # Add the new association to the session
                    db.session.commit()  # Commit the changes to the database

                    print("User associated with store as Owner")
                try:
                    # Email to the logged-in user
                    user_email_msg = Message(
                        'Store Successfully Added',
                        sender=app.config['MAIL_USERNAME'],
                        recipients=[current_user.email]
                    )
                    user_email_msg.html = render_template(
                        'storeAddMail_template.html',
                        recipient_name=current_user.first_name,
                        message_body=f"Your store '{store_name}' has been successfully added to our platform.",
                        store_name=store_name,
                        store_address=store_address,
                        owner_name=owner_name,
                        gstNumber=gstNumber,
                        business_email=business_email
                    )
                    mail.send(user_email_msg)
                    print("Email sent to user.")

                    # Email to the business email
                    business_email_msg = Message(
                        'New Store Added',
                        sender=app.config['MAIL_USERNAME'],
                        recipients=[business_email]
                    )
                    business_email_msg.html = render_template(
                        'storeAddMail_template.html',
                        recipient_name=f"{store_name} Team",
                        message_body="A new store has been successfully registered on our platform with the following details:",
                        store_name=store_name,
                        store_address=store_address,
                        owner_name=owner_name,
                        gstNumber=gstNumber,
                        business_email=business_email
                    )
                    mail.send(business_email_msg)
                    print("Email sent to business email.")
                except Exception as email_error:
                    print("Error occurred while sending email:", email_error)
                    flash("Store added successfully, but failed to send notification emails.", "warning")

                return redirect(url_for('dashboard'))
            else:
                flash("No user found or not logged in", "error")
                return redirect(url_for('login'))  # Redirect to login if the user is not found

        except Exception as e:
            db.session.rollback()  # Rollback any changes if there's an error
            print("Error occurred:", e)
            flash(f"An error occurred while adding the store: {e}", "error")
            return redirect(url_for('add_store_form'))

    else:
        flash("All fields are required for adding a new store!", "error")
        return redirect(url_for('add_store_form'))

@app.route('/join_store', methods=['GET', 'POST'])
def join_store():
    if request.method == 'GET':
        return render_template('join_store.html')

    elif request.method == 'POST':
        store_code = request.form.get('store_code')
        current_user = User.query.filter_by(email=session.get('email')).first()

        if not current_user:
            flash("User not found or not logged in!", "error")
            return redirect(url_for('join_store'))

        if not store_code:
            flash("Store code is required to join a store!", "error")
            return redirect(url_for('join_store'))

        try:
            store_to_join = Store.query.filter_by(unique_code=store_code).first()

            if store_to_join:
                print(f"Store found: {store_to_join.store_name}, Business Email: {store_to_join.business_email}")

                # Check if the user is already associated with the store
                existing_association = UserStore.query.filter_by(
                    user_id=current_user.id, store_id=store_to_join.id
                ).first()

                if not existing_association:
                    # Create a new association for the user with the store
                    new_association = UserStore(
                        user_id=current_user.id,
                        store_id=store_to_join.id,
                        role_name="Employee"  # Default role
                    )
                    db.session.add(new_association)
                    db.session.commit()

                    flash(f"You have successfully joined the store '{store_to_join.store_name}' as an Employee!", "success")

                    # Send email to the business owner about the new employee
                    business_email = store_to_join.business_email
                    join_store_email_msg = Message(
                        'New Employee Joined Your Business using InvenHub',
                        sender=app.config['MAIL_USERNAME'],
                        recipients=[business_email]
                    )
                    join_store_email_msg.html = render_template(
                        'joinstoreMail.html',
                        owner_name=store_to_join.owner_name,
                        employee_name=f"{current_user.first_name} {current_user.last_name}",
                        employee_email=current_user.email
                    )

                    try:
                        mail.send(join_store_email_msg)
                        print(f"Email sent successfully to {business_email}")
                    except Exception as e:
                        print(f"Failed to send email: {e}")
                        flash(f"Failed to send email: {e}", "error")

                    return redirect(url_for('dashboard'))

                else:
                    flash("You are already associated with this store!", "warning")
            else:
                flash("Invalid store code. Please check and try again.", "error")

        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {e}", "error")

        return redirect(url_for('join_store'))


@app.route('/account')
def account():
    if 'user' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    email = session['email']
    user = User.query.filter_by(email=email).first()
    
    if user is None:
        return redirect(url_for('dashboard'))  # If user doesn't exist, redirect to dashboard
    
    stores = user.stores  # Fetch all stores associated with the user
    
    # Debugging statement to see the stores
    print("Stores:", stores)

    return render_template('account_details.html', username=session['user'], email=session['email'], user=user, stores=stores)


@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if request.method == 'GET':
        # Fetch the current user based on session
        current_user = User.query.filter_by(email=session.get('email')).first()
        if not current_user:
            flash("User not logged in. Please log in first.", "danger")
            return redirect(url_for('login'))

        # Fetch the user's associated store
        user_store = UserStore.query.filter_by(user_id=current_user.id).first()
        if not user_store:
            flash("No store associated with this user. Please join or create a store first.", "danger")
            return redirect(url_for('add_store_form'))

        # Fetch the products for the user's store
        store = Store.query.filter_by(id=user_store.store_id).first()
        if not store:
            flash("Store not found.", "danger")
            return redirect(url_for('dashboard'))

        # Fetch all categories and their products for this store
        categories = Category.query.filter_by(store_id=store.id).all()
        products = Product.query.join(Category).with_for_update().filter(Category.store_id == store.id).all()
        # Calculate dashboard metrics
        total_products = len(products)
        top_selling = 5  # Placeholder, replace with actual logic
        low_stock = sum(1 for product in products if product.stock < 10)  

        return render_template(
            'inventory.html',
            products=products,
            categories=categories,  # Pass categories to template
            total_products=total_products,
            top_selling=top_selling,
            low_stock=low_stock,
        )

    elif request.method == 'POST':
        # You can handle POST requests for adding or updating products here
        pass

@app.route('/new_product', methods=['GET', 'POST'])
def new_product():
    if request.method == 'GET':
        # Fetch the current user and store
        current_user = User.query.filter_by(email=session.get('email')).first()
        user_store = UserStore.query.filter_by(user_id=current_user.id).first()
        store_id = user_store.store_id
        print(f"GET: Current user: {current_user.email}, Store ID: {store_id}")  # Debug
        return render_template('new_product.html', store_id=store_id)

    elif request.method == 'POST':
        try:
            # Fetch the current user
            current_user = User.query.filter_by(email=session.get('email')).first()
            if not current_user:
                flash("User not logged in. Please log in first.", "danger")
                return redirect(url_for('login'))

            print(f"POST: Current user: {current_user.email}")  # Debug

            # Fetch the user's associated store
            user_store = UserStore.query.filter_by(user_id=current_user.id).first()
            if not user_store:
                flash("No store associated with this user. Please join or create a store first.", "danger")
                return redirect(url_for('add_store_form'))

            store_id = user_store.store_id
            print(f"Store ID: {store_id}")  # Debug

            # Fetch form data
            productCategory = request.form.get('productCategory')
            product_name = request.form.get('productName')
            productPrice = request.form.get('productPrice')
            productQuantity = request.form.get('productQuantity')
            quantity = int(productQuantity)
            productSellingPrice = request.form.get('productSellingPrice')

            print(f"Form Data: {productCategory}, {product_name}, {productPrice}, {productQuantity}, {productSellingPrice}")  # Debug

            if productCategory and product_name and productPrice and productQuantity and productSellingPrice and quantity:
                # Check or create the category
                category = Category.query.filter_by(category_name=productCategory, store_id=store_id).first()
                if not category:
                    categories_in_store = Category.query.filter_by(store_id=store_id).all()
                    C_unique_id = f"{store_id}{len(categories_in_store)+1}"
                    category = Category(category_name=productCategory, store_id=store_id, C_unique_id=C_unique_id)
                    db.session.add(category)
                    print(f"New category created: {category.category_name}, ID: {C_unique_id}")  # Debug

                # Check or update the product
                existing_product = Product.query.filter_by(name=product_name, category_id=category.id).first()
                if existing_product:
                    existing_product.cost_price = float(productPrice)
                    existing_product.selling_price = float(productSellingPrice)
                    existing_product.stock += quantity
                    print(f"Product updated: {existing_product.name}, New Stock: {existing_product.stock}")  # Debug
                    product = existing_product
                else:
                    products_in_category = Product.query.filter_by(category_id=category.id).all()
                    P_unique_id = f"{category.C_unique_id}{len(products_in_category) + 1}"
                    product = Product(
                        name=product_name,
                        cost_price=float(productPrice),
                        stock=quantity,
                        selling_price=float(productSellingPrice),
                        category_id=category.id,
                        P_unique_id=P_unique_id
                    )
                    db.session.add(product)
                    print(f"New product added: {product.name}, Unique ID: {P_unique_id}")  # Debug

                # Track the stock addition as a transaction
                cart = {product.P_unique_id: quantity}
                transaction = Transaction(
                    store_id=store_id,
                    customer_name="System",
                    bill_number=f"ORD{store_id}{str(uuid.uuid4())[:7]}",
                    transaction_type='order',
                    payment_method='cash',
                    total_selling_price=0,
                    total_cost_price=float(productPrice) * quantity,
                    cart=cart,
                    success='yes',
                    type = 'checkout'
                )
                db.session.add(transaction)
                db.session.commit()
                print(f"Transaction added: {transaction.bill_number}, Type: {transaction.transaction_type}")  # Debug

                # Add a transaction item
                transaction_item = TransactionItem(
                    transaction_id=transaction.id,
                    product_id=product.id,
                    quantity=quantity,
                    selling_price=float(productSellingPrice),
                    cost_price=float(productPrice),
                    total_price=0,
                    total_cost_price=float(productPrice) * quantity
                )
                db.session.add(transaction_item)
                print(f"Transaction item added: Product {product.name}, Quantity: {quantity}")  # Debug

                # Commit all changes in one go
                db.session.commit()
                flash("Product and stock addition successfully processed!", "success")
                return redirect(url_for('inventory'))

        except Exception as e:
            db.session.rollback()
            print(f"Error occurred: {e}")  # Debug error
            flash("An error occurred while processing the request. Please try again.", "danger")
            return redirect(url_for('new_product'))


        
@app.route('/suggest-products', methods=['GET'])
def suggest_products():
    query = request.args.get('query', '').strip()
    store_id = request.args.get('store_id', type=int)

    if not query or not store_id:
        return jsonify({"suggestions": []})

    # Fetch matching products for the store
    products = Product.query.join(Category).filter(
        Category.store_id == store_id,
        or_(
            Product.name.ilike(f"%{query}%"),
            Product.P_unique_id.ilike(f"%{query}%")
        )
    ).limit(5).all()

# Prepare the suggestions list to include product details
    suggestions = []
    for product in products:
        suggestions.append({
            "name": product.name,  # Product name
            "selling_price": product.selling_price,  # Selling price of the product
            "cost_price": product.cost_price,
            "stock": product.stock,  # Available stock
            "product_id": product.P_unique_id,
            "manufacture_date":product.manufacture_date,
            "expiry_date": product.expire_date,
            "catagory": product.category_id

        })
    return jsonify({"suggestions": suggestions})

@app.route('/get-category-name', methods=['GET'])
def get_category_name():
    category_id = request.args.get('category_id')
    if not category_id:
        return jsonify({"category_name": ""}), 400  # Handle missing category_id

    try:
        category_id = int(category_id)  # Convert to integer
    except ValueError:
        return jsonify({"category_name": ""}), 400  # Handle invalid category_id

    category = Category.query.filter_by(id=category_id).first()
    if category:
        return jsonify({"category_name": category.category_name})
    return jsonify({"category_name": ""}), 404  # Not found


@app.route('/suggest-categories', methods=['GET'])
def suggest_categories():
    query = request.args.get('query', '').strip()
    store_id = request.args.get('store_id', type=int)

    if not query or not store_id:
        return jsonify({"suggestions": []})

    # Fetch matching categories for the store
    categories = Category.query.filter(
        Category.store_id == store_id,
        Category.category_name.ilike(f"%{query}%")  # Corrected this line
    ).limit(5).all()

    # Prepare the suggestions list to include category details
    suggestions = []
    for category in categories:
        suggestions.append({
            "name": category.category_name,  # Corrected this line
            "category_id": category.id
        })

    return jsonify({"suggestions": suggestions})

@app.route('/new_sale', methods=['GET', 'POST'])
def new_sale():
    current_user = User.query.filter_by(email=session.get('email')).first()
    if not current_user:
        flash("User not logged in. Please log in first.", "danger")
        return redirect(url_for('login'))

    user_store = UserStore.query.filter_by(user_id=current_user.id).first()
    if not user_store:
        flash("No store associated with this user. Please join or create a store first.", "danger")
        return redirect(url_for('add_store_form'))

    store_id = user_store.store_id

    if request.method == 'GET':
        # Fetch existing "due" transactions for the store
        tr = Transaction.query.with_for_update().filter_by(store_id=store_id, type="due", success="no").all()

        # Filter valid transactions (non-empty carts)
        valid_transactions = [t for t in tr if t.cart]

        # Check for an existing empty "due" transaction
        empty_transaction = next((t for t in tr if not t.cart), None)

        # Use the existing empty transaction if it exists; otherwise, create a new one
        if empty_transaction:
            print(f"Re-using empty transaction with ID: {empty_transaction.id}")  # Debug print
            new_transaction = empty_transaction
        else:
            print(f"Creating a new transaction for store_id: {store_id}")  # Debug print
            new_transaction = Transaction(
                store_id=store_id,
                customer_name="None",  # Default customer name "None"
                bill_number=f"SALE{store_id}{str(uuid.uuid4())[:6]}",
                transaction_type="Sale",
                type="due",
                total_selling_price=0,
                payment_method="cash",  # Default payment method
                success="no",
                cart={}
            )
            db.session.add(new_transaction)
            db.session.commit()
            print(f"Created transaction with ID: {new_transaction.id}")  # Debug print

        # Add the valid transactions, including the (reused or new) empty transaction, to the list
        valid_transactions.insert(0, new_transaction)

        # Debug print transactions
        print(f"Returning transactions: {valid_transactions}")
        for t in valid_transactions:
            print(f"Transaction: {t.id}, {t.customer_name}, {t.bill_number}, {t.type}, {t.cart}")

        # Render template with transactions
        return render_template('new_sale.html', store_id=store_id, transactions=valid_transactions)

    elif request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid or empty request data'}), 400

        cart_data = data.get('cart')
        id = data.get('bill_number')
        store_id = data.get('store_id')
        customer_name = data.get('customer_name')

        # Log incoming data
        print(f"Received bill_number: {id}")
        print(f"Received store_id: {store_id}")
        print(f"Received cart_data: {cart_data}")

        if not cart_data or not id or not store_id:
            return jsonify({'error': 'Missing required fields'}), 400

        transaction = Transaction.query.filter_by(id=id).first()
        if not transaction:
            print(f"No transaction found for bill_number: {id}, creating a new one.")
            transaction = Transaction(id=id, store_id=store_id, cart={})
            db.session.add(transaction)

        # Update cart
        transaction.transaction_type = "sale"
        transaction.cart = cart_data
        if customer_name:
            transaction.customer_name = customer_name

        # Ensure changes are saved
        print(f"Updated cart before commit: {transaction.cart} {transaction.customer_name=}")
        db.session.commit()
        print(f"Transaction saved with updated cart: {transaction.cart} {transaction.customer_name=}")
        session['transaction_id'] = transaction.id

        return jsonify({'message': 'Cart updated successfully'}), 200


@app.route('/get-cart-details', methods=['GET'])
def get_cart_details():
    transaction_id = request.args.get('transaction_id')
    if not transaction_id:
        return jsonify({'error': 'Transaction ID is required'}), 400

    print(f"Fetching cart details for transaction_id: {transaction_id}")

    # Use Session.get() instead of Query.get()
    transaction = db.session.query(Transaction).with_for_update().filter(Transaction.id == transaction_id).one_or_none()

    if not transaction:
        print(f"Transaction not found for ID: {transaction_id}")
        return jsonify({'error': 'Transaction not found'}), 404
    
    response = {
        'cart': transaction.cart,
        'customer_name': transaction.customer_name
    }

    print('Response:', response)  # Log the response for debugging
    return jsonify(response)


@app.route('/get-product-details', methods=['GET'])
def get_product_details():
    product_id = request.args.get('product_id')
    print(f"Fetching product details for product_id: {product_id}")  # Debug print

    if not product_id:
        return jsonify({'error': 'Product ID is required'}), 400

    product = Product.query.filter_by(P_unique_id=product_id).first()
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    print(f"Product details: {product.name}, {product.selling_price}, {product.stock}")  # Debug print

    return jsonify({
        'id': product.id,
        'name': product.name,
        'selling_price': product.selling_price,
        'stock': product.stock,
    })

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    current_user = User.query.filter_by(email=session.get('email')).first()

    if not current_user:
        print("User not logged in. Please log in first.", "danger")
        return redirect(url_for('login'))

    user_store = UserStore.query.filter_by(user_id=current_user.id).first()
    if not user_store:
        print("User store not found. Please create a store first.", "danger")
        return redirect(url_for('create_store'))
    store_id = user_store.store_id

    if not user_store:
        print("No store associated with this user. Please join or create a store first.", "danger")
        return redirect(url_for('add_store_form'))

    if request.method == 'GET':
        transaction_id = session.get('transaction_id')
        transaction = Transaction.query.get(transaction_id)

        if not transaction:
            print("No due transactions found.", "danger")
            return redirect(url_for('new_sale'))

        if transaction.success == 'yes':
            print("Transaction has already been processed.", "danger")
            return jsonify({"message": "Transaction already completed"}), 200

        products = []
        total_selling_price = 0
        for p_unique_id, quantity in transaction.cart.items():
            product = Product.query.with_for_update().filter_by(P_unique_id=p_unique_id).first()
            if product:
                product_details = {'product': product, 'quantity': quantity}
                products.append(product_details)
                total_selling_price += int(quantity) * int(product.selling_price)

        return render_template('cart.html', transaction=transaction, products=products, total_selling_price=total_selling_price)

    elif request.method == 'POST':
        # Handle JSON data from the Fetch API
        data = request.get_json()

        if not data:
            print("Invalid request data.", "danger")
            return jsonify({"error": "Invalid request"}), 400

        transaction_id = data.get('transactionId')
        payment_method = data.get('paymentMethod')
        want_bill = data.get('want_bill')

        if not transaction_id or not payment_method:
            print("Please select a transaction and payment method.", "danger")
            return jsonify({"error": "Missing transaction ID or payment method"}), 400

        transaction = Transaction.query.get(transaction_id)

        if not transaction:
            print("Transaction not found.", "danger")
            return jsonify({"error": "Transaction not found"}), 404

        # Ensure transaction hasn't been processed already
        if transaction.success == 'yes':
            print("Transaction has already been processed.", "danger")
            return jsonify({"message": "Transaction already completed"}), 200

        # Set success to "no" initially (in case something goes wrong later)
        transaction.success = 'yes'

        cart = transaction.cart
        total_selling_price = 0
        transaction_items = []  # List to accumulate transaction items for batch commit
        all_stock_available = True  # Flag to track if all stock is available

        # Iterate through the cart and check stock
        for unique_id, quantity in cart.items():
            product = Product.query.filter_by(P_unique_id=unique_id).first()

            if not product or int(product.stock) < int(quantity):
                print(f"Invalid product or insufficient stock for ID {unique_id}.", "danger")
                all_stock_available = False
                break  # If any product is unavailable, stop processing

            # Deduct stock and create transaction item
            cost_price = product.cost_price  # Assuming `cost_price` is available in your Product model
            
            # If cost_price is not available, you may need to handle this case.
            if cost_price is None:
                cost_price = 0
            # Deduct stock and create transaction item
            product.stock -= int(quantity)  # Deduct the stock
            transaction_item = TransactionItem(
                transaction_id=transaction.id,
                product_id=product.id,
                quantity=quantity,
                cost_price=cost_price, 
                selling_price=product.selling_price,
                total_price=quantity * product.selling_price,
                total_cost_price = quantity * cost_price
            )
            transaction_items.append(transaction_item)
            total_selling_price += transaction_item.total_price

        if not all_stock_available:
            print("Some products are out of stock. Transaction failed.", "danger")
            return jsonify({"error": "Insufficient stock for some products."}), 400

        # Update transaction details (calculated server-side)
        transaction.payment_method = payment_method
        transaction.total_selling_price = total_selling_price

        if want_bill == "yes":
            transaction.type = "bill"
            try:
                db.session.commit()  # Commit the change immediately to set the type to 'bill'
                print("Transaction type set to 'bill'.", "info")

                # Use threading or a task queue like Celery for the delayed change
                from threading import Timer

                def reset_transaction_type():
                    with app.app_context():  # Ensure the app context is available
                        # Query the transaction from the database
                        transaction_to_reset = Transaction.query.get(transaction_id)
                        if transaction_to_reset and transaction_to_reset.type == "bill":
                            # Reset the transaction type after the timer
                            transaction_to_reset.type = "checkout"
                            try:
                                db.session.commit()  # Commit the change to reset the type
                                print("Transaction type reset to 'checkout'.", "info")
                            except Exception as e:
                                db.session.rollback()  # Rollback in case of any error
                                print(f"Failed to reset transaction type: {e}", "danger")

                # Schedule the type reset after 30 seconds
                Timer(10, reset_transaction_type).start()

            except Exception as e:
                db.session.rollback()  # Rollback in case of any error setting the type to 'bill'
                print(f"Failed to set transaction type to 'bill': {e}", "danger")
                return jsonify({"error": str(e)}), 500

        else:
            # Proceed with the usual checkout process if 'want_bill' is not 'yes'
            transaction.type = "checkout"

        try:
            db.session.add_all(transaction_items)  # Add all transaction items in bulk
            db.session.commit()  # Commit changes to the database for transaction items
            print("Transaction completed successfully.", "success")
            return jsonify({"message": "Transaction completed successfully"}), 200
        except Exception as e:
            db.session.rollback()  # Rollback in case of any error
            print(f"An error occurred: {e}", "danger")
            return jsonify({"error": str(e)}), 500
        
from flask import request, jsonify

@app.route("/transactions", methods=["GET", "POST"])
def transaction():
    # Check if the user is logged in
    current_user = User.query.filter_by(email=session.get('email')).first()
    if not current_user:
        flash("User not logged in. Please log in first.", "danger")
        return redirect(url_for('login'))  # Redirect to login page

    # Check if the user has an associated store
    user_store = UserStore.query.filter_by(user_id=current_user.id).first()
    if not user_store:
        flash("User store not found. Please create or join a store first.", "danger")
        return redirect(url_for('create_store'))  # Redirect to store creation page

    store_id = user_store.store_id

    # Get the type from query parameters (default to 'order')
    transaction_type = request.args.get('type', 'order').lower()

    # Handle GET request
    if request.method == 'GET':
        # Fetch transactions with necessary fields
        transactions = (
            db.session.query(
                Transaction.bill_number,
                Transaction.last_updated,
                Transaction.transaction_date,
                Transaction.customer_name,
                Transaction.total_selling_price,
                Transaction.payment_method,
                Transaction.type.label("type"),
            )
            .filter(
                Transaction.store_id == store_id,
                func.lower(Transaction.transaction_type) == transaction_type,
            )
            .order_by(func.coalesce(Transaction.last_updated, Transaction.transaction_date).desc())
            .all()
        )

        if not transactions:
            flash(f"No transactions found for type '{transaction_type}'.", "info")
            return render_template('transaction.html', transactions=[])

        # Process transactions into a dictionary for rendering
        processed_transactions = [
            {
                "bill_number": t.bill_number,
                "last_updated": t.last_updated.strftime('%Y-%m-%d %H:%M:%S') if t.last_updated else t.transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                "customer_name": t.customer_name or "N/A",
                "total_selling_price": t.total_selling_price or 0.0,
                "payment_method": t.payment_method or "N/A",
                "type": t.type,
            }
            for t in transactions
        ]

        # Render the template with the processed transactions
        return render_template('transaction.html', transactions=processed_transactions)

    # Handle POST request (for Print functionality)
    if request.method == 'POST':
        try:
            data = request.get_json()  # Parse the incoming JSON data
            bill_number = data.get('transaction_id')
            print(bill_number)
            transaction = Transaction.query.filter_by(bill_number=bill_number).first()
            print(transaction)
            transaction_id = transaction.id
            transaction.type = "bill"
            try:
                db.session.commit()  # Commit the change immediately to set the type to 'bill'
                print("Transaction type set to 'bill'.", "info")

                # Use threading or a task queue like Celery for the delayed change
                from threading import Timer

                def reset_transaction_type():
                    with app.app_context():  # Ensure the app context is available
                        # Query the transaction from the database
                        transaction_to_reset = Transaction.query.get(transaction_id)
                        if transaction_to_reset and transaction_to_reset.type == "bill":
                            # Reset the transaction type after the timer
                            transaction_to_reset.type = "checkout"
                            try:
                                db.session.commit()  # Commit the change to reset the type
                                print("Transaction type reset to 'checkout'.", "info")
                            except Exception as e:
                                db.session.rollback()  # Rollback in case of any error
                                print(f"Failed to reset transaction type: {e}", "danger")

                # Schedule the type reset after 30 seconds
                Timer(10, reset_transaction_type).start()

            except Exception as e:
                db.session.rollback()  # Rollback in case of any error setting the type to 'bill'
                print(f"Failed to set transaction type to 'bill': {e}", "danger")
                return jsonify({"error": str(e)}), 500
            return jsonify({"message": "Invoice printed successfully", "bill_number": bill_number}), 200
        
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/esp-api/print', methods=['GET'])
def esp_api_print():
    try:
        store_id = request.args.get('store_id')
        if not store_id:
            return jsonify({"message": "store_id is required"}), 400

        store_id = int(store_id)  # Ensure it's an integer

        store = Store.query.filter_by(id=store_id).first()

        if not store:
            return jsonify({"message": f"Store with ID {store_id} not found."}), 404

        transaction = Transaction.query.filter_by(store_id=store_id, type="bill").first()

        # Handle case where no valid transaction is found
        if not transaction:
            response = {"message": "No valid bill transaction found for the store."}
            return jsonify(response), 404

        # Process products and calculate total selling price
        products = []
        total_selling_price = 0

        for p_unique_id, quantity in transaction.cart.items():
            product = Product.query.filter_by(P_unique_id=p_unique_id).first()
            if product:
                products.append({
                    'name': product.name,
                    'quantity': quantity,
                    'price': product.selling_price
                })
                total_selling_price += int(quantity) * int(product.selling_price)
            else:
                print(f"Warning: Product with ID {p_unique_id} not found.")

        # Prepare the response
        response = {
            "store":{ "store_name":store.store_name,
                     "store_address":store.store_address
                          },
            "transaction": {
                "id": transaction.bill_number,
                "customerName": transaction.customer_name,
                "date": transaction.transaction_date.strftime("%Y-%m-%d %H:%M:%S")
            },
            "products": products,
            "total_selling_price": total_selling_price,
            "payment_method": transaction.payment_method
        }

        return jsonify(response), 200

    except Exception as e:
        # Log the error and return a message
        print(f"Error: {e}")
        return jsonify({"message": "Internal Server Error"}), 500

    
@app.route('/6007')
def view_users():
    if 'user' not in session:
        return redirect(url_for('login'))

    email = session['email']
    user = User.query.filter_by(email=email).first()

    if user.role_name.lower() != 'user':

        # Fetch all users and stores from the database
        users = User.query.all()
        stores = Store.query.all()
        db_size = calculate_database_size()

        # Prepare store details with owners and employees
        store_details = []
        for store in stores:
            store_info = {
                "id": store.id,
                "name": store.store_name,
                "address": store.store_address,
                "owner": None,
                "employees": [],
                "store_code" : store.unique_code
            }

            for user in store.users:
                # Fetch the role of the user for this store
                association = db.session.query(UserStore).filter_by(user_id=user.id, store_id=store.id).first()
                role = association.role_name if association else None

                if role == "Owner":
                    store_info["owner"] = f"{user.first_name} {user.last_name}"
                elif role == "Employee":
                    store_info["employees"].append(f"{user.first_name} {user.last_name}")

            store_details.append(store_info)

        # Debugging
        print("Store Details:", store_details)
        if db_size is not None:
            db_size_value = float(db_size.split()[0])
        else:
            db_size_value = 0.0  # Or some default value depending on your logic
    
        db_size_mb = db_size_value / 1024 
        db_size_mb_str = f"{db_size_mb:.2f} MB"

        # Debugging
        print("Store Details:", store_details)
        print("db size Details:", db_size_mb_str)
        users = User.query.all()

        return render_template('view_users.html', users=users, store_details=store_details , db_size=db_size_mb_str)
    else:
        return "You are not authorized to perform this action.", 403

@app.route('/make_user_role/<int:user_id>', methods=['POST'])
def make_user_role(user_id):
    if 'email' not in session:
        flash("Please log in to continue.", "error")
        return redirect(url_for('login'))
    
    current_user = User.query.filter_by(email=session.get('email')).first()

    if current_user.role_name.lower() != 'user':
        user_to_update = User.query.get(user_id)
        if not user_to_update:
            flash("User not found.", "error")
            return redirect(url_for('view_users'))

        try:
            # Toggle role
            if user_to_update.role_name.lower() == "user":
                user_to_update.role_name = "Admin"
                flash(f"{user_to_update.first_name} {user_to_update.last_name} has been made an Admin.", "success")
            else:
                user_to_update.role_name = "User"
                flash(f"{user_to_update.first_name} {user_to_update.last_name} has been made a User.", "success")
            
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while updating the user's role: {e}", "error")

        return redirect(url_for('view_users'))
    else:
        return "You are not authorized to perform this action.", 403

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    current_user = User.query.filter_by(email=session['email']).first()

    if current_user.role_name.lower() != 'user':  # Only admins can delete users
        user = User.query.get(user_id)
        if not user:
            flash("User not found.")
            return redirect(url_for('view_users'))

        try:
            # Delete UserStore associations explicitly
            associations = UserStore.query.filter_by(user_id=user.id).all()
            for association in associations:
                db.session.delete(association)

            # Delete the user
            db.session.delete(user)
            db.session.commit()
            flash("User and associated data deleted successfully.")
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while deleting the user: {e}")

        return redirect(url_for('view_users'))
    else:
        return "You are not authorized to perform this action.", 403



@app.route('/delete_store/<int:store_id>', methods=['POST'])
def delete_store(store_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    email = session['email']
    user = User.query.filter_by(email=email).first()

    # Ensure the user is authorized
    if user.role_name.lower() != 'user':
        store = Store.query.get(store_id)
        if store:
            try:
                # Step 1: Delete associated UserStore entries
                user_store_associations = UserStore.query.filter_by(store_id=store.id).all()
                for association in user_store_associations:
                    db.session.delete(association)

                # Step 2: Delete related categories and products
                for category in store.categories:
                    for product in category.products:
                        db.session.delete(product)
                    db.session.delete(category)
                
                # Step 3: Delete the store
                db.session.delete(store)
                db.session.commit()

                flash('Store and its related data deleted successfully', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f"An error occurred while deleting the store: {e}", 'error')
        else:
            flash('Store not found', 'error')
        
        return redirect(url_for('view_users'))  # Adjust redirect as necessary
    else:
        return "You are not authorized to perform this action.", 403


@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('email', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
