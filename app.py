from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = '123456'  # Change this to a random secret key

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user_info.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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

        # Hash the password before saving
        hashed_password = generate_password_hash(password)

        # Save user data to the database
        new_user = User(first_name=first_name, last_name=last_name, email=email, phone=phone, password=hashed_password)
        try:
            db.session.add(new_user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return "Email already exists!", 400

        # Store the user's first name and email in the session
        session['user'] = first_name
        session['email'] = email  # Store email in session

        return redirect(url_for('login'))
    
    return render_template('signup.html')

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

# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('email', None)  # Clear email from session
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
