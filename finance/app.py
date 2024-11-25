import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import datetime
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
@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    stocks=db.execute("select symbol, sum(shares) as total_shares from transactions where user_id=:user_id group by symbol having total_shares>0", user_id=session["user_id"])
    cash=db.execute("select cash from users where id=:user_id", user_id=session["user_id"])[0]["cash"]
    total_value=cash
    grand_total=cash
    for stock in stocks:
        quote=lookup(stock["symbol"])
        stock["name"]=quote["name"]
        stock["price"]=quote["price"]
        stock["value"]=stock["price"]*stock["total_shares"]
        total_value+=stock["value"]
        grand_total+=stock["value"]


    return render_template("index.html", stocks=stocks, cash=usd(cash), total_value=total_value, grand_total=usd(grand_total))



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        shares=request.form.get("shares")
        if not symbol:
            return apology("Must provide symbol")
        elif not shares or not shares.isdigit() or int(shares)<=0:
            return apology("must provide a positive integer number of shares")

        quote = lookup(symbol)
        if quote is None:
            return apology("Invalid stock symbol")

        price=quote["price"]
        total_cost=int(shares)*price
        cash=db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=session["user_id"])[0]["cash"]

        if cash<total_cost:
            return apology("not enough cash")


        db.execute("UPDATE users SET cash = cash - :total_cost WHERE id = :user_id", total_cost=total_cost, user_id=session["user_id"])
        db.execute("INSERT INTO transactions (user_id, symbol, shares, price) VALUES (:user_id, :symbol, :shares, :price)",
                   user_id=session["user_id"], symbol=symbol, shares=shares, price=price)

        flash(f"Bought {shares} shares of {symbol} for {usd(total_cost)}")
        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = db.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY timestamp DESC" , session["user_id"])
    return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("Must provide username", 400)

        if not request.form.get("password"):
            return apology("Must provide password", 400)

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("Invalid username and/or password", 400)

        session["user_id"] = rows[0]["id"]

        return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        quote=lookup(symbol)
        if not quote:
            return apology("Must provide symbol", 400)
        return render_template("quote.html", quote=quote)
    else:
        return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Check if fields are filled out correctly
        if not username:
            return apology("Must provide username", 400)
        elif not password:
            return apology("Must provide password", 400)
        elif password != confirmation:
            return apology("Passwords do not match", 400)

        # Check if the username already exists
        existing_user = db.execute("SELECT * FROM users WHERE username = ?", username)
        if existing_user:
            return apology("Username already exists", 400)

        # Insert new user into database
        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, generate_password_hash(password))

        # Log the new user in automatically
        new_user = db.execute("SELECT * FROM users WHERE username = ?", username)
        session["user_id"] = new_user[0]["id"]

        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    stocks=db.execute("select symbol, SUM(shares) as total_shares from transactions where user_id= :user_id group by symbol having total_shares>0", user_id=session["user_id"])
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")
        if not symbol:
            return apology("Must provide symbol")
        elif not shares or not shares.isdigit() or int(shares) <= 0:
            return apology("Invalid number of shares")
        else:
            shares = int(shares)

        for stock in stocks:
            if stock["symbol"]==symbol:
                if stock["total_shares"]<shares:
                    return apology("not enough shares")
                else:
                    quote=lookup(symbol)
                    if quote is None:
                        return apology("symbol not found")
                    price=quote["price"]
                    total_sale=price*shares
                    db.execute ("UPDATE users SET cash=cash+:total_sale WHERE id==:user_id", total_sale=total_sale, user_id=session["user_id"])

                    db.execute("INSERT into transactions (user_id, symbol, shares, price) Values (:user_id, :symbol, :shares, :price)", user_id=session["user_id"], symbol=symbol, shares=shares, price=price)
                    flash(f"sold {shares} shares of {symbol} for {usd(total_sale)}!")
                    return redirect("/")
        return apology ("symbol not found")

    else:
        return render_template("sell.html", stocks=stocks)
