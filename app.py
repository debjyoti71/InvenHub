from flask import Flask, render_template, request, redirect, url_for, flash, session
import csv
import os

app = Flask(__name__)
app.secret_key = '123456'  # Change this to a random secret key

# Function to read users from CSV
def read_users_from_csv():
    if not os.path.exists('user_info.csv'):
        return []
    with open('user_info.csv', mode='r') as file:
        csv_reader = csv.reader(file)
        return [row for row in csv_reader]

# Function to write user to CSV
def write_user_to_csv(username, password):
    with open('user_info.csv', mode='a', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow([username, password])

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = read_users_from_csv()

        # Check if user already exists
        for user in users:
            if user[0] == username:
                flash('Username already exists!', 'error')
                return redirect(url_for('signup'))

        write_user_to_csv(username, password)
        flash('Signup successful! Please log in.', 'success')
        return redirect(url_for('home'))

    return render_template('signup.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    users = read_users_from_csv()

    for user in users:
        if user[0] == username and user[1] == password:
            session['username'] = username  # Store username in session
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))  # Redirect to the dashboard/homepage

    flash('Invalid username or password', 'error')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    # Ensure the user is logged in before accessing this page
    if 'username' not in session:
        flash('You need to log in first!', 'error')
        return redirect(url_for('home'))

    return render_template('dashboard.html', username=session['username'])

@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove user from session
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
