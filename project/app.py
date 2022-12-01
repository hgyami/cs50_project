import os
from os.path import join, dirname, realpath
import pandas as pd
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, url_for, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import logging

from helpers import apology, login_required, usd


logging.basicConfig(filename)

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies) and set up debugging mode
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["DEBUG"] = True
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///frenmo.db")

#Set up upload folder for csv files from users
# Upload folder
UPLOAD_FOLDER = '/static/files'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.after_request
def after_request(response):

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    #See your transactions rendered with some JS charts and other information about your transactions


    return apology("Please upload your Venmo records")


@app.route("/friends", methods=["GET", "POST"])
@login_required
def friends():
    # Lookup your friends that you have sent money to and see how much you have sent to each

    # Establish variable for user ID
    id = session["user_id"]

    if request.method == "POST":

        # Check whether name is inputted
        if not request.form.get("friend"):
            return apology("must enter a name")

        # Ensure username not in existing database
        friend = db.execute("SELECT transaction_id FROM transactions WHERE user_id = ? AND from_person = ? OR to_person = ?", id, request.form.get("friend"), request.form.get("friend"))
        if friend == []:
            return apology("name doesn't exist in database")

        # Set variable and redirect to result page
        friend = request.form.get("friend")
        return render_template("/search_friends.html", friend=friend)

    # User reached route via GET (as by clicking a link or via redirect)
    return render_template("/friends.html")


@app.route("/upload", methods=["GET", "POST"])
@login_required
def uploadFiles():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # get the uploaded file
        november_2022 = request.files['november_2022']
        october_2022 = request.files['october_2022']
        september_2022 = request.files['september_2022']

        logging.debug(november_2022.filename)

        if november_2022.filename != '':
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(november_2022.filename))
            logging.debug(file_path)
            # set the file path
            november_2022.save(file_path)
            # save the file
            #parseCSV(file_path)
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    return render_template("/upload.html")


#def parseCSV(filePath):
      # Establish variable for user ID
#      id = session["user_id"]
      # CSV Column Names
#      col_names = ['ID','Datetime','Type', 'Status', 'Note', 'From', 'To', 'Amount (total)', 'Amount (tip)', 'Amount (tax)', 'Tax Rate', 'Tax Exempt', 'Funding Source', 'Destination', 'Beginning Balance', 'Ending Balance', 'Statement Period Venmo Fees', 'Terminal Location', 'Year to Date Venmo Fees', 'Disclaimer']
#      # Use Pandas to parse the CSV file
#      csvData = pd.read_csv(filePath,names=col_names, header=None)
      # Loop through the rows in the csv
#      for row in csvData.iterrows():
             #Insert each row into the database
             #If there is already content in the database then append to the end of the database
#             db.execute("INSERT INTO transactions (user_id, transaction_id, date_time, transaction_type, status, note, from_person, to_person, amount_total, amount_tip, amount_tax, tax_rate, tax_exempt, funding_source, destination, beginning_balance, ending_balance, statement_period_venmo_fees, terminal_location, year_to_date_venmo_fees, disclaimer) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
#                   id, transaction_id, date_time, transaction_type, status, note, from_person, to_person, amount_total, amount_tip, amount_tax, tax_rate, tax_exempt, funding_source, destination, beginning_balance, ending_balance, statement_period_venmo_fees, terminal_location, year_to_date_venmo_fees, disclaimer)


@app.route("/login", methods=["GET", "POST"])
def login():

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password")

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


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure username not in existing database
        usernames = db.execute("SELECT username FROM users WHERE username = ?", request.form.get("username"))
        if usernames != []:
            return apology("username already taken")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # Ensure passwords match
        elif not request.form.get("confirmation") == request.form.get("password"):
            return apology("passwords do not match")

        # Set up variables for DB insert
        username = request.form.get("username")
        password = request.form.get("password")
        hash = generate_password_hash(password)

        # Insert to DB
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)

        return redirect("/upload.html")

    else:

        return render_template("register.html")


@app.route("/chgpassw", methods=["GET", "POST"])
@login_required
def change_password():

    # Establish variable for user ID
    id = session["user_id"]

    if request.method == "POST":

        # Ensure password was submitted
        if not request.form.get("password"):
            return apology("must provide password")

        # Ensure passwords match
        elif not request.form.get("check_password") == request.form.get("password"):
            return apology("passwords do not match")

        # Set up variables based on user input
        new_password = request.form.get("password")
        new_hash = generate_password_hash(new_password)

        # Update the database with the new details
        db.execute("UPDATE users SET hash = ? WHERE id = ?", new_hash, id)

        return redirect("/")

    else:

        return render_template("chgpassw.html")
