from flask import Flask, render_template, request, redirect, url_for, session
import csv
import os

app = Flask(__name__)
app.secret_key = '123456'  # Change this to a random secret key

# Define the specific user who can view other users
ALLOWED_USER = 'debjyoti2ghosh@gmail.com'
PREDEFINED_PASSWORD = '321'  # Set the predefined password for admin
CSV_FILE = 'static/user_info.csv'

# Ensure the CSV file exists with headers
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['First Name', 'Last Name', 'Email', 'Phone', 'Password'])

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

        # Save user data to CSV
        with open(CSV_FILE, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([first_name, last_name, email, phone, password])

        # Store the user's first name and email in the session
        session['user'] = first_name
        session['email'] = email  # Store email in session

        return redirect('/dashboard')
    
    return render_template('signup.html')

# Handle login form submission
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check for the predefined admin credentials
        if username == ALLOWED_USER and password == PREDEFINED_PASSWORD:
            session['user'] = 'Admin'  # Store 'Admin' as the display name for admin
            session['email'] = ALLOWED_USER  # Store admin email in session
            return redirect(url_for('dashboard'))

        # Check if the user exists in the CSV
        with open(CSV_FILE, mode='r') as file:
            reader = csv.reader(file)
            # Skip the header row
            next(reader)
            for row in reader:
                # Check the correct indexes based on your CSV structure
                if row[2] == username and row[4] == password:  # row[2] is Email, row[4] is Password
                    session['user'] = row[0]  # Store the first name in the session
                    session['email'] = row[2]  # Store the user's email in the session
                    return redirect(url_for('dashboard'))

        return "Invalid credentials, please try again."

    return render_template('login.html')

# Dashboard (only accessible to logged-in users)
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['user'], email=session['email'])


# View users (only accessible to admin)
@app.route('/view_users')
def view_users():
    # Check if the user is logged in
    if 'user' not in session:
        return redirect(url_for('login'))

    # Check if the logged-in user is allowed to view the users
    if session['email'] != ALLOWED_USER:  # Check email instead of user name
        return "You are not authorized to view this page.", 403  # Return a 403 Forbidden status

    users = []
    # Read the users from the CSV
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='r') as file:
            reader = csv.reader(file)
            # Skip the header row
            #next(reader)  
            users = list(reader)

    return render_template('view_users.html', users=users)

# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('email', None)  # Clear email from session
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
