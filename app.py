from datetime import datetime

from flask import Flask, request, jsonify
import re
import sqlite3
import bcrypt

app = Flask(__name__)

def is_current_user(username):
    conn = get_db_connection()
    c = conn.cursor()

    # Retrieve the hashed password for the username
    c.execute('SELECT username FROM users WHERE username = ?', (username,))
    result = c.fetchone()

    if result is None:
        return False
    else:
        return True

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9._%+-]*@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_username(username):
    violations = {
        "min_length": False,
        "max_length": False,
        "invalid characters or format": False,
        "consecutive underscores or dots": False
    }
    # Rule 1: Length at least 3 characters
    if len(username) <= 3:
        violations["min_length"] = True

    # Rule 2: Length no more than 15 characters
    if len(username) > 15:
        violations["max_length"] = True

    # Rule 3: Formatting and valid characters.
    # 3a Must start with a lower or upper case letter
    # 3b After the first letter, any number of letters, numbers, dots, or underline symbols are allowed
    # 3c Cannot contain other special characters other than dot or underline
    # 3d Must end with letter or number.
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9._]*[a-zA-Z0-9]$", username):
        violations['invalid characters or format'] = True

    # Rule 4: Must not contain consecutive underscores or dots
    if "__" in username or ".." in username:
        violations["consecutive underscores or dots"] = True

    # Additional checks (e.g., profanity filter) can be added here

    # Check if all violations are False, meaning all rules are met
    if not any(violations.values()):
        return "valid"
    else:
        return violations

def is_valid_password(password):
    # Dictionary to store rule violations
    violations = {
        "min_length": False,
        "max_length": False,
        "uppercase": False,
        "lowercase": False,
        "digit": False,
        "special_char": False,
        "no_sequential": False,
        "no_repeated_chars": False
    }

    # Rule 1: Length at least 8 characters
    if len(password) < 8:
        violations["min_length"] = True

    # Rule 2: Length no more than 40
    if len(password) > 40:
        violations["max_length"] = True

    # Rule 3: At least one uppercase letter
    if not re.search(r'[A-Z]', password):
        violations["uppercase"] = True

    # Rule 4: At least one lowercase letter
    if not re.search(r'[a-z]', password):
        violations["lowercase"] = True

    # Rule 5: At least one digit
    if not re.search(r'[0-9]', password):
        violations["digit"] = True

    # Rule 6: At least one special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        violations["special_char"] = True

    # Rule 7: No sequential characters (e.g., "123" or "abc")
    # Using regex to check for sequences of 3+ ascending letters or digits
    sequential_pattern = r'(012|123|234|345|456|567|678|789|abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)'
    if re.search(sequential_pattern, password.lower()):
        violations["no_sequential"] = True

    # Rule 8: No repeated consecutive characters (e.g., "aa" or "11")
    if re.search(r'(.)\1', password):
        violations["no_repeated_chars"] = True

    # Check if all violations are False, meaning all rules are met
    if not any(violations.values()):
        return "valid"
    else:
        return violations

def create_user(username, email, password):
    # Connect to the SQLite database
    conn = get_db_connection()
    c = conn.cursor()

    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Insert the username and hashed password into the users table
    try:
        c.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', (username, email, hashed_password))
        conn.commit()  # Commit the changes
        print(f'User "{username}" has been added to the database.')
    except sqlite3.IntegrityError:
        print(f'Error: Username "{username}" already exists.')
        raise ValueError("User already exists")
    finally:
        conn.close()  # Close the connection

    return True


def authenticate_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()

    # Retrieve the hashed password for the username
    c.execute('SELECT password FROM users WHERE username = ?', (username,))
    result = c.fetchone()

    if result:
        hashed_password = result[0]
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
            return 'valid'
        else:
            # print("Invalid password.")
            return {'valid': False, 'message': 'Incorrect password.'}
    else:
        # print("Username not found.")
        return {'valid': False, 'message': 'Username does not exist.'}


def delete_user(username, password):
    # Step 1: Authenticate the user
    auth_result = authenticate_user(username, password)
    if auth_result != 'valid':
        # Authentication failed
        return {'success': False, 'message': 'Authentication failed. Cannot delete user.'}

    # Step 2: Connect to the database
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    try:
        # Step 3: Delete the user record from the database
        c.execute('DELETE FROM users WHERE username = ?', (username,))
        conn.commit()

        # Check if a row was actually deleted
        if c.rowcount == 0:
            return {'success': False, 'message': 'User not found. No deletion occurred.'}

        # Deletion successful
        return {'success': True, 'message': f'User "{username}" successfully deleted.'}

    except sqlite3.Error as e:
        # Handle potential database errors
        return {'success': False, 'message': f'Error deleting user: {e}'}

    finally:
        # Step 4: Close the database connection
        conn.close()

@app.route('/')
def home():
    return jsonify({'message': 'OK'}), 200

@app.route('/users', methods=['POST'])
def create_user_route():
    data = request.get_json()

    if 'username' not in data or 'password' not in data or 'email' not in data:
        return jsonify({'error': 'Username, email, and password fields are required'}), 400

    username = data['username']
    password = data['password']
    email = data['email']

    # Validate email format
    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    # Validate password
    pw_valid = is_valid_password(password)
    if pw_valid != 'valid':
        return jsonify({'error': 'Invalid password format', 'reasons': pw_valid}), 400

    # Validate username
    username_valid = is_valid_username(username)
    if username_valid != 'valid':
        return jsonify({'error': 'Invalid username format', 'reasons': username_valid}), 400

    # Call the insert_user function to create a new user
    try:
        create_user(username, email, password)
        return jsonify({'message': f'User "{username}" created successfully.'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# under real conditions this would almost certainly be a GET request
# but I wanted to give you an example of POST that matches the other
# API endpoints in the test cases
@app.route('/users/check_username', methods=['POST'])
def check_username_route():
    data = request.get_json()

    if 'username' not in data:
        return jsonify({'error': 'Username field is required'}), 400
    username = data['username']

    user = is_current_user(username)

    if user:
        return jsonify({'exists': True, 'username': username}), 200
    else:
        return jsonify({'exists': False, 'username': username}), 404


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password fields are required'}), 400

    username = data['username']
    password = data['password']

    result = authenticate_user(username, password)

    if result == 'valid':
        return jsonify({'valid': True, 'message': 'Login successful!'}), 200
    else:
        return jsonify({'valid': result['valid'], 'message': result['message']}), 400

def get_db_connection():
    conn = sqlite3.connect('users.db')
    return conn

if __name__ == '__main__':
    app.run()