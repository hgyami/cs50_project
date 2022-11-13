# Personal touch: Allow users to change password.

import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():

    id = session["user_id"]

    # Clear the old portfolio table records once the user refreshes the page
    db.execute("DELETE FROM portfolio")

    # Query transactions database to understand what the current portfolio looks like
    current_portfolio = db.execute(
        "SELECT symbol, SUM(shares) AS shares FROM transactions WHERE user_id = ? AND shares > 0 GROUP BY symbol", id)

    # Populate the portfolio table row by row
    for stock in current_portfolio:
        symbol = stock["symbol"]
        search = lookup(symbol)
        stock_name = search["name"]
        shares = int(stock["shares"])
        price = search["price"]
        holding_value = price*shares
        db.execute("INSERT INTO portfolio (user_id, symbol, stock_name, shares, price, holding_value) VALUES (?,?,?,?,?,?)",
                   id, symbol, stock_name, shares, price, holding_value)

    # Query the portfolio table to render the currently owned stocks in the top table on index.html
    stocks = db.execute("SELECT symbol, stock_name, shares, price, holding_value FROM portfolio WHERE user_id = ?", id)

    # Query the user table to render the current cash balance
    money_left = db.execute("SELECT cash FROM users WHERE id = ?", id)
    money_left = money_left[0]["cash"]

    # Query the portfolio table and loop over result to calculate the current total value of the portfolio
    holding_value = db.execute("SELECT holding_value FROM portfolio WHERE id = ?", id)

    portfolio_value = 0
    for row in holding_value:
        portfolio_value = portfolio_value + int(row["holding_value"])

    # Calculate the total wealth of the investor
    total_wealth = money_left + portfolio_value

    return render_template("index.html", stocks=stocks, money_left=money_left, portfolio_value=portfolio_value, total_wealth=total_wealth)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    if request.method == "POST":

        # Check whether stock symbol is inputted
        if not request.form.get("symbol"):
            return apology("must enter stock symbol")

        # Check that an integer is inputted
        elif not request.form.get("shares"):
            return apology("must enter number of shares")

        # Check that a positive integer is inputted
        elif int(request.form.get("shares")) < 1:
            return apology("must enter positive integer")

        # Initialize all relevant variables checking along the way that a user has inputted the right stock symbol
        id = session["user_id"]
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))
        trans_type = "buy"

        if lookup(symbol) == None:
            return apology("must provide valid stock symbol")

        else:
            search = lookup(symbol)

        stock_name = search["name"]
        price = search["price"]
        purchase = price*shares

        # Call db to calculate how much money user has left
        # Note that response is a list so need to select the right item
        money_left = db.execute("SELECT cash FROM users WHERE id = ?", id)
        money_left = money_left[0]["cash"]

        # Check user has enough funds left to make the purchase
        if money_left < purchase:
            return apology("insufficient funds")

        # Insert fields into transactions table
        db.execute("INSERT INTO transactions (user_id, symbol, stock_name, shares, price, type) VALUES (?,?,?,?,?,?)",
                   id, symbol, stock_name, shares, price, trans_type)

        # Update money left in database
        money_left = money_left - purchase
        db.execute("UPDATE users SET cash = ? WHERE id = ?", money_left, id)

        return redirect("/")

    else:

        return render_template("buy.html")


@app.route("/history")
@login_required
def history():

    id = session["user_id"]

    # Query database to generate list of transactions
    transactions = db.execute("SELECT symbol, stock_name, shares, price, type, time FROM transactions WHERE user_id = ?", id)

    # Pass list into html template
    return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():

    if request.method == "POST":

        # Check whether stock symbol is inputted
        if not request.form.get("symbol"):
            return apology("must enter stock symbol")

        # Set variables and lookup symbol from JSON
        symbol = request.form.get("symbol")

        if lookup(symbol) == None:
            return apology("must provide valid stock symbol")

        else:
            stock = lookup(symbol)

        return render_template("quoted.html", stock=stock)

    else:

        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure passwords match
        elif not request.form.get("check_password") == request.form.get("password"):
            return apology("passwords do not match", 403)

        # Set up variables for DB insert
        username = request.form.get("username")
        password = request.form.get("password")
        hash = generate_password_hash(password)

        # Insert to DB
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)

    else:

        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    id = session["user_id"]

    if request.method == "POST":

        symbol = request.form.get("symbol")
        sell_shares = int(request.form.get("shares"))*-1

        portfolio = db.execute("SELECT symbol, SUM(shares) AS shares FROM portfolio WHERE user_id = ? GROUP BY symbol", id)
        for stock in portfolio:
            total_owned = int(stock["shares"])

        if not symbol:
            return apology("must select valid stock symbol", 403)

        elif not sell_shares:
            return apology("must enter number of shares")

        elif (sell_shares*-1) < 1:
            return apology("must enter positive integer")

        elif total_owned < (sell_shares*-1):
            return apology("insufficient shares to sell")

        # Initialize all relevant variables
        search = lookup(symbol)
        stock_name = search["name"]
        price = search["price"]
        sale = price*sell_shares*-1
        trans_type = "sell"

        # Call db to calculate how much money user has left
        # Note that response is a list so need to select the right item
        money_left = db.execute("SELECT cash FROM users WHERE id = ?", id)
        money_left = money_left[0]["cash"]

        # Add sale value to money left and update database
        money_left = money_left + sale
        db.execute("UPDATE users SET cash = ? WHERE id = ?", money_left, id)

        # Insert fields into transactions table
        db.execute("INSERT INTO transactions (user_id, symbol, stock_name, shares, price, type) VALUES (?,?,?,?,?,?)",
                   id, symbol, stock_name, sell_shares, price, trans_type)

        return redirect("/")

    else:

        portfolio = db.execute("SELECT symbol FROM portfolio WHERE user_id = ?", id)

        # How to return just the second half of the dict??!!!

        return render_template("sell.html", portfolio=portfolio)


@app.route("/chgpassw", methods=["GET", "POST"])
@login_required
def change_password():

    if request.method == "POST":

        # Ensure password was submitted
        if not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure passwords match
        elif not request.form.get("check_password") == request.form.get("password"):
            return apology("passwords do not match", 403)

        id = session["user_id"]

        # Set up variables based on user input
        new_password = request.form.get("password")
        new_hash = generate_password_hash(new_password)

        # Update the database with the new details
        db.execute("UPDATE users SET hash = ? WHERE id = ?", new_hash, id)

        return redirect("/")

    else:

        return render_template("chgpassw.html")