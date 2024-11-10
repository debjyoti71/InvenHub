from flask import Flask, render_template, request, redirect, url_for, session ,flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
import random

app = Flask(__name__)
app.secret_key = '123456'  # Change this to a random secret key

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user_info.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'sparksofficial.bd@gmail.com'
app.config['MAIL_PASSWORD'] = 'ktiy ghvz qbno lzwp'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)

# Define the User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Create the database and tables
with app.app_context():
    db.create_all()

# Define the specific user who can view other users
ALLOWED_USER = 'debjyoti2ghosh@gmail.com'
PREDEFINED_PASSWORD = '321'  # Set the predefined password for admin

# Route for home page
@app.route('/')
def home():
    return render_template('home.html')

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
    msg = Message('Your OTP Code', sender='your-email@gmail.com', recipients=[email])
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
                    return redirect(url_for('dashboard'))

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
        if email == ALLOWED_USER and password == PREDEFINED_PASSWORD:
            session['user'] = 'Admin'  # Store 'Admin' as the display name for admin
            session['email'] = ALLOWED_USER  # Store admin email in session
            return redirect(url_for('dashboard'))

        # Check if the user exists in the database
        user = User.query.filter_by(email=email).first()
        if user:
            if user and check_password_hash(user.password, password):  # Check the hashed password
                session['user'] = user.first_name  # Store the first name in the session
                session['email'] = user.email  # Store the user's email in the session
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

@app.route('/6007')
def view_users():
    # Check if the user is logged in
    if 'user' not in session:
        return redirect(url_for('login'))

    # Check if the logged-in user is allowed to view the users
    if session['email'] != ALLOWED_USER:
        return "You are not authorized to view this page.", 403

    # Retrieve all users except the admin user
    users = User.query.all()  # Retrieve all users without excluding anyone

    return render_template('view_users.html', users=users)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    # Check if the user is logged in
    if 'user' not in session:
        return redirect(url_for('login'))

    # Check if the logged-in user is allowed to delete users
    if session['email'] != ALLOWED_USER:
        return "You are not authorized to delete users.", 403

    # Retrieve the user to be deleted
    user = User.query.get(user_id)
    if not user:
        flash("User not found.")
        return redirect(url_for('view_users'))

    # Delete the user
    try:
        db.session.delete(user)
        db.session.commit()
        flash("User deleted successfully.")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while deleting the user.")

    return redirect(url_for('view_users'))

# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('email', None)  # Clear email from session
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
