import yfinance as yf
import mysql.connector
from mysql.connector import Error
import plotly.graph_objects as go
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired

app = Flask(__name__)
app.secret_key = "S@^a6"

def create_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='123',
            database='StockManagement'
        )
        if connection.is_connected():
            print("Connected to MySQL database")
            return connection

    except Error as e:
        print("Error while connecting to MySQL database:", e)
        return None

def create_tables(connection):
    try:
        cursor = connection.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio (
                symbol VARCHAR(10) PRIMARY KEY,
                quantity INTEGER,
                avg_price FLOAT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                symbol VARCHAR(10) PRIMARY KEY
            )
        ''')

        connection.commit()

    except Error as e:
        print("Error while creating tables:", e)


def add_to_portfolio(connection, symbol, quantity, avg_price):
    try:
        cursor = connection.cursor()
        cursor.execute('INSERT INTO portfolio (symbol, quantity, avg_price) VALUES (%s, %s, %s) '
                       'ON DUPLICATE KEY UPDATE quantity=quantity+VALUES(quantity), avg_price=VALUES(avg_price)',
                       (symbol, quantity, avg_price))
        connection.commit()
        print(f"Added {quantity} shares of {symbol} to the portfolio.")
    except Error as e:
        print("Error while adding to portfolio:", e)

def add_to_watchlist(connection, symbol):
    try:
        cursor = connection.cursor()
        cursor.execute('INSERT IGNORE INTO watchlist (symbol) VALUES (%s)', (symbol,))
        connection.commit()
        print(f"Added {symbol} to the watchlist.")
    except Error as e:
        print("Error while adding to watchlist:", e)

def get_portfolio(connection):
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM portfolio')
        return cursor.fetchall()
    except Error as e:
        print("Error while fetching portfolio data:", e)
        return []

def get_watchlist(connection):
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM watchlist')
        return cursor.fetchall()
    except Error as e:
        print("Error while fetching watchlist data:", e)
        return []

def get_live_price(symbol):
    try:
        stock = yf.Ticker(symbol)
        live_price = stock.history(period='1d')['Close'][0]
        return live_price
    except Exception as e:
        print(f"Error while fetching live price for {symbol}: {e}")
        return None

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')
@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        if check_user_credentials(username, password):
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form)

def check_user_credentials(username, password):
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute('SELECT * FROM users WHERE username=%s AND password=%s', (username, password))
            user = cursor.fetchone()
            cursor.close()
            if user:
                return True
    except Error as e:
        print("Error while checking user credentials:", e)
    return False
    
@app.route('/index')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    connection = create_connection()
    if connection:
        create_tables(connection)
        portfolio_data = get_portfolio(connection)
        watchlist_data = get_watchlist(connection)

        updated_portfolio_data = []
        for stock in portfolio_data:
            symbol, quantity, avg_price = stock
            live_price = get_live_price(symbol)
            if live_price is not None:
                stock_data = [symbol, quantity, avg_price, live_price]  # Create a new list with live price
            else:
                stock_data = [symbol, quantity, avg_price, "Not available"]
            updated_portfolio_data.append(stock_data)

        updated_watchlist_data = []
        for stock in watchlist_data:
            symbol = stock[0]
            live_price = get_live_price(symbol)
            if live_price is not None:
                stock_data = [symbol, live_price]  # Create a new list with live price
            else:
                stock_data = [symbol, "Not available"]
            updated_watchlist_data.append(stock_data)

        return render_template('index.html', portfolio=updated_portfolio_data, watchlist=updated_watchlist_data)


if __name__ == '__main__':
    app.run(debug=True, port=6625)

