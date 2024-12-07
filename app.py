from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import random
from dotenv import load_dotenv
import os
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
    # Render HTML Template
    msg.html = render_template(
        'otpMail_template.html',
        otp=otp  # Pass the dynamic OTP value to the template
    )

    mail.send(msg)

    return redirect(url_for('verify_otp'))

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

# Handle login form submission
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

# Dashboard (only accessible to logged-in users)
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['user'], email=session['email'])

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
        products = Product.query.join(Category).filter(Category.store_id == store.id).all()
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
        current_user = User.query.filter_by(email=session.get('email')).first()
        user_store = UserStore.query.filter_by(user_id=current_user.id).first()
        store_id = user_store.store_id
        return render_template('new_product.html', store_id=store_id)

    elif request.method == 'POST':
        # Fetch the current user based on session
        current_user = User.query.filter_by(email=session.get('email')).first()
        if not current_user:
            flash("User not logged in. Please log in first.", "danger")
            return redirect(url_for('login'))

        # Fetch the user's associated store(s)
        user_store = UserStore.query.filter_by(user_id=current_user.id).first()

        if not user_store:
            flash("No store associated with this user. Please join or create a store first.", "danger")
            return redirect(url_for('add_store_form'))

        # Fetch form data
        productCategory = request.form.get('productCategory')
        product_name = request.form.get('productName')
        productPrice = request.form.get('productPrice')
        productQuantity = request.form.get('productQuantity')
        productSellingPrice = request.form.get('productSellingPrice')

        if productCategory and product_name and productPrice and productQuantity and productSellingPrice:
            # Check if the category exists
            category = Category.query.filter_by(category_name=productCategory, store_id=user_store.store_id).first()
            if not category:
                # Create the category if it doesn't exist
                category = Category(category_name=productCategory, store_id=user_store.store_id)
                db.session.add(category)
                db.session.commit()

                # Automatically set C_unique_id after creating the category
                categories_in_store = Category.query.filter_by(store_id=user_store.store_id).all()
                for i, cat in enumerate(categories_in_store, start=1):
                    cat.C_unique_id = f"{cat.store_id}{i}"
                db.session.commit()

            # Check if the product exists
            existing_product = Product.query.filter_by(name=product_name, category_id=category.id).first()

            if existing_product:
                # Update existing product
                existing_product.cost_price = float(productPrice)  # Update cost price
                existing_product.selling_price = float(productSellingPrice)  # Update selling price
                existing_product.stock += int(productQuantity)  # Add to stock
                db.session.commit()
                flash("Product updated successfully!", "success")
            else:
                # Add new product
                new_product = Product(
                    name=product_name,
                    cost_price=float(productPrice),
                    stock=int(productQuantity),
                    selling_price=float(productSellingPrice),
                    category_id=category.id,
                )

                # Set P_unique_id before committing
                products_in_category = Product.query.filter_by(category_id=category.id).all()
                new_product.P_unique_id = f"{category.C_unique_id}{len(products_in_category) + 1}"

                db.session.add(new_product)
                db.session.commit()

                flash("Product added successfully!", "success")

            # Now, track the stock addition as a transaction (order)
            # Add a new transaction (order) to represent this stock addition
            transaction = Transaction(
                store_id=user_store.store_id,  # Correct reference to the store ID
                customer_name="System",  # No customer for stock addition
                bill_number=f"ORD{str(uuid.uuid4())[:8]}",  # Unique order bill number
                transaction_type='order',  # Set type as order
                payment_method='cash',  # Assume cash for stock additions
                total_selling_price=0,  # No selling price for stock additions
                total_cost_price=float(productPrice) * int(productQuantity),  # Total cost price for the added stock
                success = 'yes'
            )

            db.session.add(transaction)
            db.session.commit()

            # Create a transaction item to track this stock addition for the product
            transaction_item = TransactionItem(
            transaction_id=transaction.id,  # Correct reference to the transaction ID
            product_id=(new_product.id if 'new_product' in locals() else existing_product.id),  # Conditional assignment for product ID
            quantity=int(productQuantity),  # Quantity added to stock
            selling_price=float(productSellingPrice),  # Selling price used for stock addition (for future sales)
            cost_price=float(productPrice),  # Cost price used for stock addition
            total_price=0,  # No selling price for stock additions
            total_cost_price=float(productPrice) * int(productQuantity),  # Total cost price for this product
            profit=0  # No profit for stock additions
        )
            db.session.add(transaction_item)
            db.session.commit()

            flash("Stock addition (order) tracked successfully!", "success")
            return redirect(url_for('inventory'))
        
@app.route('/suggest-products', methods=['GET'])
def suggest_products():
    query = request.args.get('query', '').strip()
    store_id = request.args.get('store_id', type=int)

    if not query or not store_id:
        return jsonify({"suggestions": []})

    # Fetch matching products for the store
    products = Product.query.join(Category).filter(
        Category.store_id == store_id,
        Product.name.ilike(f"%{query}%")
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
            "expiry_date": product.expire_date

        })
    return jsonify({"suggestions": suggestions})

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
    if request.method == 'GET':
        # Fetch the current user and associated store
        current_user = User.query.filter_by(email=session.get('email')).first()
        if not current_user:
            flash("User not logged in. Please log in first.", "danger")
            return redirect(url_for('login'))

        user_store = UserStore.query.filter_by(user_id=current_user.id).first()
        if not user_store:
            flash("No store associated with this user. Please join or create a store first.", "danger")
            return redirect(url_for('add_store_form'))

        store_id = user_store.store_id

        # Initialize transaction if not yet initialized
        session_transaction_id = session.get('transaction_id')
        transaction = None
        if session_transaction_id:
            # Try to find an existing transaction with the session ID and success = "no"
            transaction = Transaction.query.filter_by(id=session_transaction_id, success="no").first()
            if transaction:
                print(f"Found existing transaction with ID: {transaction.id}")
            else:
                # If no transaction found, check for other transactions with success="no"
                transaction = Transaction.query.filter_by(success="no").first()
                if transaction:
                    print(f"Found existing transaction with no success: {transaction.id}")
                else:
                    print("No transaction found with success='no', creating a new one.")
                    # Create a new transaction if none found
                    new_transaction = Transaction(
                        store_id=store_id,
                        customer_name="System",  # Default customer name
                        bill_number=f"SALE{str(uuid.uuid4())[:8]}",  # Unique bill number
                        transaction_type="sale",  # Default to 'sale' transaction type
                        total_selling_price=0,
                        payment_method="cash",  # Default payment method
                        success="no"  # Initially marked as unsuccessful
                    )
                    db.session.add(new_transaction)
                    db.session.commit()

                    # Store the transaction ID in the session
                    session['transaction_id'] = new_transaction.id
                    transaction = new_transaction
                    print(f"Created new transaction with ID: {transaction.id}")
        else:
            print("No session transaction ID found, checking for other transactions with success='no'.")
            transaction = Transaction.query.filter_by(success="no").first()
            if transaction:
                print(f"Found existing transaction with no success: {transaction.id}")
            else:
                print("No transaction found with success='no', creating a new one.")
                # Create a new transaction if none found
                new_transaction = Transaction(
                    store_id=store_id,
                    customer_name="System",  # Default customer name
                    bill_number=f"SALE{str(uuid.uuid4())[:8]}",  # Unique bill number
                    transaction_type="sale",  # Default to 'sale' transaction type
                    total_selling_price=0,
                    payment_method="cash",  # Default payment method
                    success="no"  # Initially marked as unsuccessful
                )
                db.session.add(new_transaction)
                db.session.commit()

                # Store the transaction ID in the session
                session['transaction_id'] = new_transaction.id
                transaction = new_transaction
                print(f"Created new transaction with ID: {transaction.id}")
                
        return render_template('new_sale.html', store_id=store_id, transaction=transaction)
        # session['cart'] = cart_data
        # print(f"Cart data saved to session: {session.get('cart')}")
        # return redirect(url_for('checkout'))

    elif request.method == 'POST':
        # Fetch the current user
        current_user = User.query.filter_by(email=session.get('email')).first()
        if not current_user:
            flash("User not logged in. Please log in first.", "danger")
            return redirect(url_for('login'))

        user_store = UserStore.query.filter_by(user_id=current_user.id).first()
        if not user_store:
            flash("No store associated with this user. Please join or create a store first.", "danger")
            return redirect(url_for('add_store_form'))

        # Fetch the transaction using session
        transaction = db.session.get(Transaction, session.get('transaction_id'))
        if not transaction:
            flash("Transaction not found.", "danger")
            return redirect(url_for('new_sale'))

        print(f"Transaction found for POST: {transaction.id}")

        # Fetch cart data from the request JSON
        cart_data = request.get_json().get('cart')
        if not cart_data:
            flash("No cart data provided.", "danger")
            return redirect(url_for('new_sale'))

        print(f"Cart Data received: {cart_data}")

        # Validate the cart data (check if product_id and quantity are present)
        try:
            cart_data = {key: int(value) for key, value in cart_data.items()}  # Convert string quantities to integers
            print(f"Converted cart data: {cart_data}")
        except ValueError:
            flash("Invalid product or quantity input.", "danger")
            print("Invalid cart data. Redirecting to new_sale...")
            return redirect(url_for('new_sale'))

        # Ensure cart data is valid
        if not all(isinstance(value, int) and value > 0 for value in cart_data.values()):
            flash("Invalid product or quantity input.", "danger")
            print("Invalid cart data. Redirecting to new_sale...")
            return redirect(url_for('new_sale'))

        # Store selected products in the session (for use in checkout)
        session['cart'] = cart_data  # Save the cart dictionary in session
        print(f"Cart data saved to session: {session.get('cart')}")

        # Redirect to checkout page
        print("Redirecting to checkout...")
        return redirect(url_for('checkout'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'GET':
        print("GET request received on /checkout")
        # Fetch the current user and associated store
        current_user = User.query.filter_by(email=session.get('email')).first()
        if not current_user:
            flash("User not logged in. Please log in first.", "danger")
            return redirect(url_for('login'))

        user_store = UserStore.query.filter_by(user_id=current_user.id).first()
        if not user_store:
            flash("No store associated with this user. Please join or create a store first.", "danger")
            return redirect(url_for('add_store_form'))

        store_id = user_store.store_id

        # Fetch the transaction from session
        transaction = db.session.get(Transaction, session.get('transaction_id'))
        if not transaction:
            flash("Transaction not found.", "danger")
            return redirect(url_for('new_sale'))

        print(f"Transaction found for checkout: {transaction.id}")

        # Retrieve cart from session
        cart = session.get('cart', [])
        if not cart:
            flash("Cart is empty.", "danger")
            return redirect(url_for('new_sale'))

        # Calculate total selling price
        total_selling_price = 0
        products = []
        for unique_id, quantity in cart.items():
            product = Product.query.filter_by(P_unique_id=unique_id).first()
            if product:
                total_price = product.selling_price * quantity
                total_selling_price += total_price
                products.append({
                    'product': product,
                    'quantity': quantity,
                    'total_price': total_price,
                })

        print(f"Total selling price: {total_selling_price}")

        return render_template('cart.html', store_id=store_id, transaction=transaction, products=products, total_selling_price=total_selling_price)

    elif request.method == 'POST':
        # Handle payment confirmation as before
        payment_method = request.form.get('payment_method')
        if not payment_method:
            flash("Please select a payment method.", "danger")
            return redirect(url_for('checkout'))

        transaction = Transaction.query.get(session.get('transaction_id'))
        if not transaction:
            flash("Transaction not found.", "danger")
            return redirect(url_for('new_sale'))

        cart = session.get('cart', [])
        total_selling_price = 0
        total_cost_price = 0

        for unique_id, quantity in cart.items():
            product = Product.query.filter_by(P_unique_id=unique_id).first()
            new_quantity = int(quantity)

            if not product or new_quantity <= 0:
                flash(f"Invalid product or quantity for product ID {unique_id}.", "danger")
                continue

            # Check if the selected quantity exceeds the available stock
            if product.stock < new_quantity:
                flash(f"Insufficient stock for product '{product.name}'. Available stock: {product.stock}.", "danger")
                continue

            # Deduct stock
            product.stock -= new_quantity

            # Create transaction item
            transaction_item = TransactionItem(
                transaction_id=transaction.id,
                product_id=product.id,
                quantity=new_quantity,
                selling_price=product.selling_price,
                cost_price=product.cost_price,
                total_price=new_quantity * product.selling_price,
                total_cost_price=new_quantity * product.cost_price,
            )
            db.session.add(transaction_item)

            # Update totals
            total_selling_price += transaction_item.total_price
            total_cost_price += transaction_item.total_cost_price  # Corrected the typo here

        # Ensure the transaction's total selling price is initialized if needed
        if transaction.total_selling_price is None:
            transaction.total_selling_price = 0  # Initialize if None

        # Update transaction totals and finalize
        transaction.payment_method = payment_method
        transaction.total_selling_price += total_selling_price
        transaction.success = "yes"  # Mark transaction as successful
        print(f"{transaction.success=}, {transaction.total_selling_price=},{transaction.payment_method =}")

        db.session.commit()

        # Clear the cart session data
        session.pop('cart', None)

        flash("Transaction completed successfully.", "success")
        return redirect(url_for('dashboard'))

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
