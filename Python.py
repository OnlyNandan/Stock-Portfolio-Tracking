import yfinance as yf
import mysql.connector
from mysql.connector import Error
import plotly.graph_objects as go
from flask import Flask, render_template, request, redirect, url_for

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

if __name__ == '__main__':
    connection = create_connection()
    if connection:
        create_tables(connection)

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
        return stock.history(period='1d')['Close'][0]
    except Exception as e:
        print(f"Error while fetching live price for {symbol}: {e}")
        return None


def display_portfolio_and_watchlist(connection):
    portfolio_data = get_portfolio(connection)
    watchlist_data = get_watchlist(connection)

    print("\nPortfolio:")
    for stock in portfolio_data:
        symbol, quantity, avg_price = stock
        live_price = get_live_price(symbol)
        if live_price is not None:
            print(f"{symbol}: {quantity} shares | Avg. Price: ${avg_price:.2f} | Live Price: ${live_price:.2f}")
        else:
            print(f"{symbol}: {quantity} shares | Avg. Price: ${avg_price:.2f} | Live Price: Not available")

    print("\nWatchlist:")
    for stock in watchlist_data:
        symbol = stock[0]
        live_price = get_live_price(symbol)
        if live_price is not None:
            print(f"{symbol}: Live Price: ${live_price:.2f}")
        else:
            print(f"{symbol}: Live Price: Not available")



