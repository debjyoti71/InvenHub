from flask import Flask, request, render_template, redirect
import csv
import os 

app = Flask(__name__)

# In-memory user database (will be populated from CSV)
database = {}

# Function to load users from CSV and create the file if it doesn't exist
def initialize_csv():
    if not os.path.exists('user_info.csv'):
        # Create the CSV file with headers if it doesn't exist
        with open('user_info.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Username", "Password"])
    else:
        # Load existing users into the in-memory database from CSV
        with open('user_info.csv', 'r') as file:
            reader = csv.reader(file)
            # Check if the CSV is empty except for the header
            if not any(reader):  # Check if there are no rows after the header
                return  # Exit the function if the file is empty
            next(reader)  # Skip the header
            for row in reader:
                if len(row) == 2:  # Check for valid username and password rows
                    username, password = row
                    database[username] = password

# Initialize the CSV and the database on app start
initialize_csv()

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
        
        # Check if the user already exists in the in-memory database
        if name1 in database:
            return render_template('login.html', info='User already exists')
        else:
            # Add the new user to the in-memory database
            database[name1] = pwd
            
            # Save the new user to the CSV file
            with open('user_info.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([name1, pwd])
            
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
        
        # Check if the user exists in the in-memory database
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
    app.run()
