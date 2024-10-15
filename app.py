from flask import Flask, render_template, request, redirect, url_for, session
import csv
import os

app = Flask(__name__)
app.secret_key = '123456'  # Change this to a random secret key

# Define the specific user who can view other users
ALLOWED_USER = 'admin'
PREDEFINED_PASSWORD = '321'  # Set the predefined password for admin

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Save the new user to the CSV
        with open('user_info.csv', mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([username, password])

        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check for the predefined admin credentials
        if username == ALLOWED_USER and password == PREDEFINED_PASSWORD:
            session['username'] = username
            return redirect(url_for('dashboard'))

        # Check if the user exists in the CSV
        with open('user_info.csv', mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                if row[0] == username and row[1] == password:
                    session['username'] = username
                    return redirect(url_for('dashboard'))

        return "Invalid credentials, please try again."

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])

@app.route('/view_users')
def view_users():
    if 'username' not in session:
        return redirect(url_for('login'))

    if session['username'] != ALLOWED_USER:
        return "You are not authorized to view this page."

    users = []
    # Read the users from the CSV
    if os.path.exists('user_info.csv'):
        with open('user_info.csv', mode='r') as file:
            reader = csv.reader(file)
            users = list(reader)

    return render_template('view_users.html', users=users)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
