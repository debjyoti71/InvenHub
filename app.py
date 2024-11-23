from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import random
from dotenv import load_dotenv
import os
from config import Config  # Import your Config class
from models import db, User, Store, Product , user_store
import csv 
from datetime import datetime ,timedelta
from flask_migrate import Migrate

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
    db_url = "postgresql://invenhub_h207_user:EldjNhNf9IGe5ZiFrIqF82gqTRWLN2AM@dpg-ct0n9thu0jms73c7bh2g-a.oregon-postgres.render.com/invenhub_h207"

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

    if session['email'] not in app.config['ALLOWED_USERS']:
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
        if email in app.config['ALLOWED_USERS'] and password == app.config['PREDEFINED_PASSWORD']:
            session['user'] = 'Admin'  # Store 'Admin' as the display name for admin
            session['email'] = email  # Store admin email in session
            return redirect(url_for('dashboard'))

        # Check if the user exists in the database
        user = User.query.filter_by(email=email).first()
        if user:
            if user and check_password_hash(user.password, password):  # Check the hashed password
                session['user'] = user.first_name  # Store the first name in the session
                session['email'] = user.email  # Store the user's email in the session
                 # Check if the user has an associated store
                if user.store is None:  # Assuming `user.store` returns None if no store is associated
                    return redirect(url_for('add_store_form'))
                else:
                    return redirect(url_for('dashboard'))
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
                association = db.session.query(user_store).filter_by(user_id=current_user.id, store_id=new_store.id).first()
                if not association:  # Only create the association if it does not exist
                    # Create association between the user and the store
                    db.session.execute(user_store.insert().values(user_id=current_user.id, store_id=new_store.id, role="Owner"))
                    db.session.commit()

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
            print(f"Business Email: {store_to_join.business_email}")


            if store_to_join:
                if store_to_join not in current_user.stores:
                    current_user.stores.append(store_to_join)
                    association = db.session.query(user_store).filter_by(
                        user_id=current_user.id, store_id=store_to_join.id
                    ).first()
                    if association:
                        db.session.execute(
                            user_store.update().where(
                                (user_store.c.user_id == current_user.id) & 
                                (user_store.c.store_id == store_to_join.id)
                            ).values(role="Employee")
                        )
                    db.session.commit()

                    flash(f"You have successfully joined the store '{store_to_join.store_name}' as an Employee!", "success")
                    
                    # Send email to business email about the new employee
                    business_email = store_to_join.business_email  # Replace with the store's business email address
                    join_store_email_msg = Message(
                        'New Employee Joined Your Business using InvenHub',
                        sender=app.config['MAIL_USERNAME'],
                        recipients=[business_email]
                    )
                    join_store_email_msg.html = render_template(
                        'joinstoreMail.html',
                        owner_name=f"{store_to_join.owner_name}",
                        employee_name=f"{current_user.first_name} {current_user.last_name}",
                        employee_email= current_user.email
                    )
                    try:
                        mail.send(join_store_email_msg)
                        print(f"Email sent successfully! to {business_email} message: {join_store_email_msg}")
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


@app.route('/6007')
def view_users():
    if 'user' not in session:
        return redirect(url_for('login'))

    if session['email'] not in app.config['ALLOWED_USERS']:
        return "You are not authorized to view this page.", 403

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
            association = db.session.query(user_store).filter_by(user_id=user.id, store_id=store.id).first()
            role = association.role if association else None

            if role == "Owner":
                store_info["owner"] = f"{user.first_name} {user.last_name}"
            elif role == "Employee":
                store_info["employees"].append(f"{user.first_name} {user.last_name}")

        store_details.append(store_info) 
    db_size_value = float(db_size.split()[0])   
    db_size_mb = db_size_value / 1024 
    db_size_mb_str = f"{db_size_mb:.2f} MB"

    # Debugging
    print("Store Details:", store_details)
    print("db size Details:", db_size_mb_str)

    return render_template('view_users.html', users=users, store_details=store_details , db_size=db_size_mb_str)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    if session['email'] not in app.config['ALLOWED_USERS']:
        return "You are not authorized to delete users.", 403

    user = User.query.get(user_id)
    if not user:
        flash("User not found.")
        return redirect(url_for('view_users'))

    try:
        # Step 1: Check the role of the user in each store before deleting
        for store in user.stores:
            # Query the user-store association to check the role of the user for this store
            association = db.session.query(user_store).filter_by(user_id=user.id, store_id=store.id).first()
            
            if association and association.role == 'Owner':
                # Remove the user from the store's user list
                store.users.remove(user)

                # Step 2: Delete related categories and products for stores owned by the user
                for category in store.categories:
                    # Delete related products
                    for product in category.products:
                        db.session.delete(product)
                    # Then delete the category itself
                    db.session.delete(category)

                # Delete the store only if the user is the owner
                db.session.delete(store)

        # Step 3: Finally, delete the user
        db.session.delete(user)
        db.session.commit()
        flash("User and associated data deleted successfully.")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while deleting the user: {e}")

    return redirect(url_for('view_users'))



@app.route('/delete_store/<int:store_id>', methods=['POST'])
def delete_store(store_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if session['email'] not in app.config['ALLOWED_USERS']:
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
