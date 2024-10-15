from flask import Flask, request, render_template, redirect
import sqlite3
import os 

app = Flask(__name__)

# Initialize database connection
def initialize_db():
    conn = sqlite3.connect('user_info.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Call this function on app start
initialize_db()

# Function to load users from the database
def load_users():
    conn = sqlite3.connect('user_info.db')
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM users')
    users = cursor.fetchall()
    conn.close()
    return {username: password for username, password in users}

# In-memory user database (will be populated from the database)
database = load_users()

@app.route('/')
def hello_world():
    return render_template("login.html")

# Signup route
@app.route('/form_signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        name1 = request.form['username']
        pwd = request.form['password']
        confirm_pwd = request.form['confirm-password']
        
        # Check if passwords match
        if pwd != confirm_pwd:
            return render_template('signup.html', info='Passwords do not match')
        
        # Check if the user already exists in the database
        if name1 in database:
            return render_template('login.html', info='User already exists')
        else:
            # Add the new user to the database
            conn = sqlite3.connect('user_info.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (name1, pwd))
            conn.commit()
            conn.close()
            
            # Reload users into memory
            database[name1] = pwd
            
            # After successful signup, redirect the user to the login page
            return redirect('/form_login')
    else:
        return render_template('signup.html')

# Login route
@app.route('/form_login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        name1 = request.form['username']
        pwd = request.form['password']
        
        # Check if the user exists in the database
        if name1 not in database:
            return render_template('login.html', info='Invalid User')
        elif database[name1] != pwd:
            return render_template('login.html', info='Invalid Password')
        else:
            # Render the home page after successful login
            return render_template('home.html', name=name1)
    else:
        return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)
