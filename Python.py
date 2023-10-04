import yfinance as yf
import mysql.connector
from mysql.connector import Error
import plotly.graph_objects as go
import requests
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
            password='123'
        )
        if connection.is_connected():
            print("Connected to MySQL database")
            create_db_query = "CREATE DATABASE IF NOT EXISTS stockmanagement"
            cursor = connection.cursor()
            cursor.execute(create_db_query)
            cursor.close()

            connection = mysql.connector.connect(
                host='localhost',
                user='root',
                password='123',
                database='stockmanagement'
                
            )
            if connection.is_connected():
                print("Connected to 'stockmanagement' database")
                return connection

    except Error as e:
        print("Error while connecting to MySQL database:", e)
        return None

def create_tables(connection):
    try:
        cursor = connection.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(100) NOT NULL
            )
        ''')

        cursor.execute('''
            INSERT IGNORE INTO users (username, password)
            VALUES ('Nandan', 'nandan7'),
                   ('Sohana', 'sohana6'),
                   ('Nayonika', 'nayonika3')
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                symbol VARCHAR(10),
                quantity INTEGER,
                avg_price FLOAT,
                FOREIGN KEY (user_id) REFERENCES users(id))
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                symbol VARCHAR(10) PRIMARY KEY
            )
        ''')

        connection.commit()

    except Error as e:
        print("Error while creating tables:", e)


def add_to_portfolio(connection, user_id, symbol, new_quantity, new_avg_price):
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT quantity, avg_price FROM portfolio WHERE user_id=%s AND symbol=%s', (user_id, symbol))
        result = cursor.fetchone()

        if result:
            old_quantity, old_avg_price = result
            total_old_cost = old_quantity * old_avg_price
            total_new_cost = new_quantity * new_avg_price
            total_cost = total_old_cost + total_new_cost
            total_quantity = old_quantity + new_quantity
            combined_avg_price = total_cost / total_quantity

            cursor.execute('''
                UPDATE portfolio 
                SET quantity=%s, avg_price=%s 
                WHERE user_id=%s AND symbol=%s
            ''', (total_quantity, combined_avg_price, user_id, symbol))

        else:
            cursor.execute('''
                INSERT INTO portfolio (user_id, symbol, quantity, avg_price)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, symbol, new_quantity, new_avg_price))

        connection.commit()
        print(f"Added {new_quantity} shares of {symbol} to the portfolio with avg price of {new_avg_price if not result else combined_avg_price}.")
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

def get_portfolio(connection, user_id):
    try:
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM portfolio WHERE user_id=%s', (user_id,))
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
def get_user_id(username):
    try:
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            cursor.execute('SELECT id FROM users WHERE username=%s', (username,))
            user = cursor.fetchone()
            cursor.close()
            if user:
                return user[0]
    except Error as e:
        print("Error while getting user ID:", e)
    return None

@app.route('/index')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    user_id = get_user_id(username) 
    if user_id is not None:
        connection = create_connection()
        if connection:
            create_tables(connection)
            portfolio_data = get_portfolio(connection, user_id) 
            watchlist_data = get_watchlist(connection)

            updated_portfolio_data = []
            for stock in portfolio_data:
                ida,uida,symbol, quantity, avg_price = stock
                live_price = get_live_price(symbol)
                if live_price is not None:
                    stock_data = [symbol, quantity, avg_price, live_price] 
                else:
                    stock_data = [symbol, quantity, avg_price, "Not available"]
                updated_portfolio_data.append(stock_data)

            updated_watchlist_data = []
            for stock in watchlist_data:
                symbol = stock[0]
                live_price = get_live_price(symbol)
                if live_price is not None:
                    stock_data = [symbol, live_price]  
                else:
                    stock_data = [symbol, "Not available"]
                updated_watchlist_data.append(stock_data)

            return render_template('index.html', portfolio=updated_portfolio_data, watchlist=updated_watchlist_data)
    
    flash('Error fetching data. Please try again later.', 'danger')
    return redirect(url_for('login'))

def get_financial_news(api_key):
    try:
        url = f'https://newsapi.org/v2/top-headlines?category=business&language=en&apiKey={api_key}'
        response = requests.get(url)
        data = response.json()
        if data['status'] == 'ok':
            return [article['title'] for article in data['articles']]
        else:
            return []
    except Exception as e:
        print(f"Error while fetching financial news: {e}")
        return []



@app.route('/portfolio')
def portfolio_page():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    user_id = get_user_id(username) 
    if user_id is not None:
        connection = create_connection()
        if connection:
            create_tables(connection)
            portfolio_data = get_portfolio(connection, user_id) 
            watchlist_data = get_watchlist(connection)

            total_value_of_stocks = sum(stock[3] * get_live_price(stock[2]) if get_live_price(stock[2]) is not None else 0 for stock in portfolio_data)
            total_investment = sum(stock[3] * stock[4] for stock in portfolio_data)
            total_gains = total_value_of_stocks - total_investment

            updated_portfolio_data = []
            for stock in portfolio_data:
                ida,uida,symbol, quantity, avg_price = stock
                live_price = get_live_price(symbol)
                if live_price is not None:
                    stock_data = [symbol, quantity, avg_price, live_price]  
                else:
                    stock_data = [symbol, quantity, avg_price, "Not available"]
                updated_portfolio_data.append(stock_data)

            api_key = 'a85aaff62a0846f1860b12eae398880f'  
            financial_news = get_financial_news(api_key)

            return render_template(
                'portfolio.html',
                portfolio=updated_portfolio_data,
                total_value_of_stocks=total_value_of_stocks,
                total_investment=total_investment,
                total_gains=total_gains,
                financial_news=financial_news
            )
            return render_template('portfolio.html', portfolio=updated_portfolio_data,
                               total_value_of_stocks=total_value_of_stocks, total_investment=total_investment,
                               total_gains=total_gains)
    
    flash('Error fetching data. Please try again later.', 'danger')
    return redirect(url_for('login'))



@app.route('/add_stock', methods=['POST'])
def add_stock():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        symbol = request.form.get('symbol')
        quantity = int(request.form.get('quantity'))
        avg_price = float(request.form.get('avg_price'))
        
        username = session['username']
        user_id = get_user_id(username)
        
        if is_valid_stock(symbol):
            connection = create_connection()
            if connection:
                symbol=symbol.upper()
                add_to_portfolio(connection, user_id, symbol, quantity, avg_price)
        else:
            flash(f"Invalid stock symbol: {symbol}. Please enter a valid stock symbol.", 'danger')
    
    return redirect(url_for('portfolio_page'))
def is_valid_stock(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        if info.get('quoteType') in ('EQUITY', 'ETF'):
            return True
        else:
            return False
    except Exception as e:
        print(f"Error while validating stock symbol {symbol}: {e}")
        return False


def delete_stock_from_portfolio(connection, symbol_to_delete):
    try:
        cursor = connection.cursor()
        cursor.execute('DELETE FROM portfolio WHERE symbol=%s', (symbol_to_delete,))
        connection.commit()
        print(f"Deleted {symbol_to_delete} from the portfolio.")
    except Error as e:
        print("Error while deleting stock from portfolio:", e)

@app.route('/delete_stock', methods=['POST'])
def delete_stock():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        symbol_to_delete = request.form.get('symbol')
        connection = create_connection()
        if connection:
            delete_stock_from_portfolio(connection, symbol_to_delete)
            flash(f"Deleted {symbol_to_delete} from the portfolio.", 'success')
    
    return redirect(url_for('portfolio_page'))





if __name__ == '__main__':
    connection = create_connection()
    
    if connection:
        create_tables(connection)
        connection.close()
    
    app.run(debug=True, port=1281)
