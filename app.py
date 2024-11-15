from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import random
from dotenv import load_dotenv
import os
from config import Config  # Import your Config class
from models import db, User, Store, Product
import csv 
from datetime import datetime

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

# Route for home page
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/7006')
def config():
    if 'user' not in session:
        return redirect(url_for('login'))

    if session['email'] != app.config['ALLOWED_USER']:
        return "You are not authorized to view this page.", 403
    
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
    msg = Message('Your OTP Code', sender=app.config['MAIL_USERNAME'], recipients=[email])
    msg.body = f'Your OTP code is: {otp}'
    mail.send(msg)
    
    return redirect(url_for('verify_otp'))

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        otp = ''.join([request.form[f'otp{i}'] for i in range(1, 7)])  # Combine OTP digits

        # Check if the entered OTP matches the one in session
        if 'otp' in session and otp == str(session['otp']):
            session.pop('otp', None)  # Clear OTP after successful verification

            # Now save the user's data to the database after OTP verification
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
            if user and check_password_hash(user.password, password):  # Check the hashed password
                session['user'] = user.first_name  # Store the first name in the session
                session['email'] = user.email  # Store the user's email in the session
                return redirect(url_for('add_store_form'))
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
    return render_template('business_profile.html')  # HTML file for the add store form

@app.route('/add_store', methods=['POST'])
def add_store():
    print("Form data received:", request.form)  # Debugging line

    store_name = request.form.get('store_name')
    store_address = request.form.get('store_address')
    owner_name = request.form.get('owner_name')
    gstNumber = request.form.get('gstNumber')
    business_email = request.form.get('business_email')

    print("Store Name:", store_name)
    print("Store Address:", store_address)
    print("Owner Name:", owner_name)
    print("GST Number:", gstNumber)
    print("Business Email:", business_email)

    # Check if all fields are provided
    if store_name and store_address and owner_name and gstNumber and business_email:
        try:
            # Create new store
            new_store = Store(store_name=store_name, store_address=store_address, owner_name=owner_name, gstNumber=gstNumber, business_email=business_email)
            db.session.add(new_store)
            db.session.commit()
            db.session.flush()

            # Assuming the current user is logged in, associate the store with the logged-in user
            current_user = User.query.filter_by(email=session.get('email')).first()  # Get the current logged-in user
            if current_user:
                current_user.stores.append(new_store)  # Associate the new store with the user
                db.session.commit()
                flash("Store added and associated with you successfully!", "success")
                return redirect(url_for('dashboard'))
            else:
                print("User not found!", "error")
                flash("User not found!", "error")       
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {e}", "error")
            return redirect(url_for('add_store_form'))
        
        return redirect(url_for('dashboard'))
    else:
        print("All fields are required!", "error")
        flash("All fields are required!", "error")
        return redirect(url_for('add_store_form'))

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


@app.route('/6007')
def view_users():
    if 'user' not in session:
        return redirect(url_for('login'))

    if session['email'] != app.config['ALLOWED_USER']:
        return "You are not authorized to view this page.", 403
    
    # Fetch all users and stores from the database
    users = User.query.all()
    stores = Store.query.all()
    
    # Debug: Print the number of users and stores fetched
    print(f"Total users found: {len(users)}")
    print(f"Total stores found: {len(stores)}")

    # Debug: Iterate over the users and print the associated stores
    for user in users:
        print(f"User: {user.first_name} {user.last_name}, Stores: {[store.store_name for store in user.stores]}")
    
    # Debug: Print the list of stores
    print("Stores List:")
    for store in stores:
        print(f"Store ID: {store.id}, Name: {store.store_name}, Address: {store.store_address}")
    
    return render_template('view_users.html', users=users, stores=stores)


@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    if session['email'] != app.config['ALLOWED_USER']:
        return "You are not authorized to delete users.", 403

    user = User.query.get(user_id)
    if not user:
        flash("User not found.")
        return redirect(url_for('view_users'))

    try:
        # Step 1: Remove the user-store association
        for store in user.stores:
            store.users.remove(user)

            # Step 2: Delete related categories and products
            for category in store.categories:
                # Delete related products
                for product in category.products:
                    db.session.delete(product)
                # Then delete the category itself
                db.session.delete(category)

            # Optionally delete the store
            db.session.delete(store)
        
        # Step 3: Finally, delete the user
        db.session.delete(user)
        db.session.commit()
        flash("User, associated stores, categories, and products deleted successfully.")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while deleting the user: {e}")

    return redirect(url_for('view_users'))


@app.route('/delete_store/<int:store_id>', methods=['POST'])
def delete_store(store_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if session['email'] != app.config['ALLOWED_USER']:
        return "You are not authorized to perform this action.", 403
    
    store = Store.query.get(store_id)
    if store:
        try:
            # Step 1: Delete related products
            for category in store.categories:
                for product in category.products:
                    db.session.delete(product)
                # Step 2: Delete categories
                db.session.delete(category)
            
            # Step 3: Finally, delete the store
            db.session.delete(store)
            db.session.commit()
            flash('Store and related products and categories deleted successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while deleting the store: {e}", 'error')
    else:
        flash('Store not found', 'error')
    
    return redirect(url_for('view_users'))


@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('email', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
