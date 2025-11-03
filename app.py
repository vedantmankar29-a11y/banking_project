from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
import random
import string
from decimal import Decimal
import os # <-- IMPORT THE 'os' MODULE

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') # <-- CHANGE: Use an environment variable

# --- Database Configuration ---
# CHANGE: Get database details from environment variables
db_config = {
    'host': os.environ.get('DB_HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'database': os.environ.get('DB_NAME')
}

def get_db_connection():
    """Establishes a connection to the database."""
    conn = mysql.connector.connect(**db_config)
    return conn

# --- Helper Functions ---
def generate_captcha():
    """Generates a simple 6-character alphanumeric CAPTCHA."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def get_next_available_account_number():
    """Finds the smallest available account number."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT account_number FROM customers ORDER BY account_number ASC")
    existing_numbers = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    if not existing_numbers:
        return 1
    expected_number = 1
    for num in existing_numbers:
        if num != expected_number:
            return expected_number
        expected_number += 1
    return expected_number

# --- Main Routes ---
@app.route('/')
def home():
    if 'user_type' in session:
        if session['user_type'] == 'customer':
            return redirect(url_for('customer_dashboard'))
        elif session['user_type'] == 'employee':
            return redirect(url_for('employee_dashboard'))
    captcha = generate_captcha()
    session['captcha'] = captcha
    return render_template('login.html', captcha=captcha)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been successfully logged out.', 'success')
    return redirect(url_for('home'))

# --- Customer Routes ---
@app.route('/customer_login', methods=['POST'])
def customer_login():
    email = request.form['email']
    password = request.form['password']
    user_captcha = request.form['captcha']
    if user_captcha != session.get('captcha'):
        flash('Invalid CAPTCHA. Please try again.', 'danger')
        return redirect(url_for('home'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM customers WHERE email = %s AND password = %s", (email, password))
    customer = cursor.fetchone()
    cursor.close()
    conn.close()
    if customer:
        session['user_id'] = customer['account_number']
        session['user_name'] = f"{customer['first_name']} {customer['last_name']}"
        session['user_type'] = 'customer'
        return redirect(url_for('customer_dashboard'))
    else:
        flash('Invalid Email ID or Password.', 'danger')
        return redirect(url_for('home'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        mobile_number = request.form['mobile_number']
        email = request.form['email']
        starting_deposit = request.form['starting_deposit']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE first_name = %s AND last_name = %s AND mobile_number = %s AND email = %s", (first_name, last_name, mobile_number, email))
        if cursor.fetchone():
             flash('An account with these details already exists. Please enter a different password if you wish to create a separate account.', 'warning')
             return render_template('signup.html')
        cursor.execute("INSERT INTO account_requests (first_name, last_name, mobile_number, email, starting_deposit, password) VALUES (%s, %s, %s, %s, %s, %s)", (first_name, last_name, mobile_number, email, starting_deposit, password))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Your account opening request has been submitted successfully! You will be notified once it is approved.', 'success')
        return redirect(url_for('home'))
    return render_template('signup.html')

@app.route('/customer/dashboard')
def customer_dashboard():
    if 'user_id' not in session or session.get('user_type') != 'customer':
        return redirect(url_for('home'))
    return render_template('customer_dashboard.html')

@app.route('/customer/view_details')
def view_details():
    if 'user_id' not in session or session.get('user_type') != 'customer':
        return redirect(url_for('home'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM customers WHERE account_number = %s", (session['user_id'],))
    account_details = cursor.fetchone()
    cursor.execute("SELECT * FROM loans WHERE account_number = %s AND status = 'approved'", (session['user_id'],))
    loans = cursor.fetchall()
    total_dues = sum(loan['total_repayment'] - loan['repayment_paid'] for loan in loans)
    cursor.close()
    conn.close()
    return render_template('view_details.html', details=account_details, loans=loans, total_dues=total_dues)

@app.route('/customer/transaction/<type>', methods=['GET', 'POST'])
def transaction(type):
    if 'user_id' not in session or session.get('user_type') != 'customer':
        return redirect(url_for('home'))
    if request.method == 'POST':
        amount = Decimal(request.form['amount'])
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT balance FROM customers WHERE account_number = %s", (session['user_id'],))
        current_balance = cursor.fetchone()['balance']
        if type == 'deposit':
            new_balance = current_balance + amount
            flash(f'Successfully deposited ₹{amount:.2f}. New balance is ₹{new_balance:.2f}.', 'success')
        elif type == 'withdraw':
            if amount > current_balance:
                flash('Insufficient balance.', 'danger')
                return redirect(url_for('transaction', type='withdraw'))
            new_balance = current_balance - amount
            flash(f'Successfully withdrew ₹{amount:.2f}. New balance is ₹{new_balance:.2f}.', 'success')
        cursor.execute("UPDATE customers SET balance = %s WHERE account_number = %s", (new_balance, session['user_id']))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('customer_dashboard'))
    return render_template('transaction.html', type=type.capitalize())

@app.route('/get_balance')
def get_balance():
    if 'user_id' in session and session['user_type'] == 'customer':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT balance FROM customers WHERE account_number = %s", (session['user_id'],))
        balance = cursor.fetchone()['balance']
        cursor.close()
        conn.close()
        return jsonify({'balance': f'₹{balance:.2f}'})
    return jsonify({'error': 'Not logged in'}), 401

@app.route('/customer/apply_loan', methods=['GET', 'POST'])
def apply_loan():
    if 'user_id' not in session or session.get('user_type') != 'customer':
        return redirect(url_for('home'))
    if request.method == 'POST':
        amount = float(request.form['amount'])
        tenure = int(request.form['tenure'])
        interest_rate = float(request.form['interest_rate'])
        total_repayment = amount * (1 + (interest_rate / 100) * tenure)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO loans (account_number, amount, tenure, interest_rate, total_repayment, status) VALUES (%s, %s, %s, %s, %s, 'pending')", (session['user_id'], amount, tenure, interest_rate, total_repayment))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Your loan application has been submitted successfully!', 'success')
        return redirect(url_for('pending_requests'))
    return render_template('apply_loan.html')

@app.route('/customer/repay_loan', methods=['GET', 'POST'])
def repay_loan():
    if 'user_id' not in session or session.get('user_type') != 'customer':
        return redirect(url_for('home'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        loan_id = request.form['loan_id']
        amount_to_repay = Decimal(request.form['amount'])

        cursor.execute("SELECT balance FROM customers WHERE account_number = %s", (session['user_id'],))
        current_balance = cursor.fetchone()['balance']
        cursor.execute("SELECT total_repayment, repayment_paid FROM loans WHERE loan_id = %s", (loan_id,))
        loan = cursor.fetchone()
        repayment_left = loan['total_repayment'] - loan['repayment_paid']

        if amount_to_repay > current_balance:
            flash('Insufficient funds in your account.', 'danger')
        elif amount_to_repay > repayment_left:
            flash(f'You cannot repay more than the amount left (₹{repayment_left:.2f}).', 'warning')
        else:
            new_balance = current_balance - amount_to_repay
            new_repayment_paid = loan['repayment_paid'] + amount_to_repay
            
            cursor.execute("UPDATE customers SET balance = %s WHERE account_number = %s", (new_balance, session['user_id']))
            cursor.execute("UPDATE loans SET repayment_paid = %s WHERE loan_id = %s", (new_repayment_paid, loan_id))
            conn.commit()
            
            flash(f'Successfully paid ₹{amount_to_repay:.2f} towards Loan ID {loan_id}.', 'success')

        cursor.close()
        conn.close()
        return redirect(url_for('repay_loan'))

    cursor.execute("SELECT * FROM loans WHERE account_number = %s AND status = 'approved'", (session['user_id'],))
    loans_data = cursor.fetchall()
    
    for loan in loans_data:
        loan['repayment_left'] = loan['total_repayment'] - loan['repayment_paid']
        
    cursor.close()
    conn.close()
    return render_template('repay_loan.html', loans=loans_data)

@app.route('/customer/pending_requests')
def pending_requests():
    if 'user_id' not in session or session.get('user_type') != 'customer':
        return redirect(url_for('home'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM loans WHERE account_number = %s ORDER BY status", (session['user_id'],))
    loan_reqs = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('pending_requests.html', loan_requests=loan_reqs)

@app.route('/customer/close_account', methods=['POST'])
def close_account():
    if 'user_id' not in session or session.get('user_type') != 'customer':
        return redirect(url_for('home'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM customers WHERE account_number = %s", (session['user_id'],))
    conn.commit()
    cursor.close()
    conn.close()
    session.clear()
    flash('Your account has been permanently closed.', 'success')
    return redirect(url_for('home'))

# --- Employee Routes ---
@app.route('/employee_login', methods=['POST'])
def employee_login():
    email = request.form['email']
    password = request.form['password']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM employees WHERE email = %s AND password = %s", (email, password))
    employee = cursor.fetchone()
    cursor.close()
    conn.close()
    if employee:
        session['user_id'] = employee['id']
        session['user_name'] = employee['name']
        session['user_type'] = 'employee'
        return redirect(url_for('employee_dashboard'))
    else:
        flash('Invalid Employee Credentials.', 'danger')
        return redirect(url_for('home'))
        
@app.route('/employee/dashboard')
def employee_dashboard():
    if 'user_id' not in session or session.get('user_type') != 'employee':
        return redirect(url_for('home'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM account_requests WHERE status = 'pending'")
    account_reqs = cursor.fetchall()
    cursor.execute("SELECT l.*, c.first_name, c.last_name FROM loans l JOIN customers c ON l.account_number = c.account_number WHERE l.status = 'pending'")
    loan_reqs = cursor.fetchall()
    cursor.execute("SELECT ar.*, c.account_number FROM account_requests ar LEFT JOIN customers c ON ar.email = c.email WHERE ar.status != 'pending'")
    completed_account_reqs = cursor.fetchall()
    cursor.execute("SELECT l.*, c.first_name, c.last_name FROM loans l JOIN customers c ON l.account_number = c.account_number WHERE l.status != 'pending'")
    completed_loan_reqs = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('employee_dashboard.html', account_requests=account_reqs, loan_requests=loan_reqs, completed_account_requests=completed_account_reqs, completed_loan_requests=completed_loan_reqs)

@app.route('/employee/handle_account_request/<int:request_id>/<action>', methods=['POST'])
def handle_account_request(request_id, action):
    if 'user_id' not in session or session.get('user_type') != 'employee':
        return redirect(url_for('home'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM account_requests WHERE request_id = %s", (request_id,))
    req = cursor.fetchone()
    if not req:
        flash('Request not found.', 'danger')
        return redirect(url_for('employee_dashboard'))
    if action == 'approve':
        account_number = get_next_available_account_number()
        cursor.execute("INSERT INTO customers (account_number, first_name, last_name, mobile_number, email, password, balance) VALUES (%s, %s, %s, %s, %s, %s, %s)", (account_number, req['first_name'], req['last_name'], req['mobile_number'], req['email'], req['password'], req['starting_deposit']))
        cursor.execute("UPDATE account_requests SET status = 'approved' WHERE request_id = %s", (request_id,))
        cursor.execute("UPDATE employees SET requests_approved = requests_approved + 1 WHERE id = %s", (session['user_id'],))
        flash(f"Account for {req['first_name']} approved with Account Number: {account_number}", 'success')
    elif action == 'deny':
        cursor.execute("UPDATE account_requests SET status = 'denied' WHERE request_id = %s", (request_id,))
        cursor.execute("UPDATE employees SET requests_denied = requests_denied + 1 WHERE id = %s", (session['user_id'],))
        flash(f"Account request for {req['first_name']} has been denied.", 'warning')
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('employee_dashboard'))

@app.route('/employee/handle_loan_request/<int:loan_id>/<action>', methods=['POST'])
def handle_loan_request(loan_id, action):
    if 'user_id' not in session or session.get('user_type') != 'employee':
        return redirect(url_for('home'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM loans WHERE loan_id = %s", (loan_id,))
    loan = cursor.fetchone()
    if not loan:
        flash('Loan request not found.', 'danger')
        return redirect(url_for('employee_dashboard'))
    if action == 'approve':
        cursor.execute("UPDATE loans SET status = 'approved' WHERE loan_id = %s", (loan_id,))
        cursor.execute("UPDATE customers SET balance = balance + %s WHERE account_number = %s", (loan['amount'], loan['account_number']))
        cursor.execute("UPDATE employees SET requests_approved = requests_approved + 1 WHERE id = %s", (session['user_id'],))
        flash(f"Loan request for Account #{loan['account_number']} approved.", 'success')
    elif action == 'deny':
        cursor.execute("UPDATE loans SET status = 'denied' WHERE loan_id = %s", (loan_id,))
        cursor.execute("UPDATE employees SET requests_denied = requests_denied + 1 WHERE id = %s", (session['user_id'],))
        flash(f"Loan request for Account #{loan['account_number']} denied.", 'warning')
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('employee_dashboard'))

@app.route('/employee/account')
def employee_account():
    if 'user_id' not in session or session.get('user_type') != 'employee':
        return redirect(url_for('home'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM employees WHERE id = %s", (session['user_id'],))
    employee_details = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('employee_account..html', details=employee_details)