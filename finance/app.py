import pytz
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)
app.debug = False

# Custom filter
app.jinja_env.filters["usd"] = usd
app.secret_key ="eriubhkjlk;f,p[[]'/f;l,;kv;io4pcre[l';3;k[fe]cso\l',k;j;nb;hjlks;zv/,m 4rju59805-7op8ikuy-0[pla:#OI4lkrgijb40[-=5]';l]]]"

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    user_id = session.get("user_id")
    cash=((db.execute("SELECT cash FROM users WHERE id=?",user_id))[0]["cash"])
    name=db.execute("SELECT username FROM users WHERE id=?",user_id)[0]["username"]
    stockOwnership=db.execute("SELECT DISTINCT symbol FROM transactions WHERE user_id=?",user_id)
    symbol=[]

    if stockOwnership :
        for i in stockOwnership:
            symbol.append(i["symbol"])
       
        shares={}
        for symbolshare in symbol:
            sum=db.execute("SELECT SUM(CASE WHEN transaction_type = 'Sell' THEN -1 * shares ELSE shares END) AS sumofshare FROM transactions WHERE  user_id=? AND symbol=?",user_id,symbolshare)
      
            if sum[0]['sumofshare']>0:
                shares[symbolshare]=sum[0]["sumofshare"]
        lookup_dict={}
        totalsharevalue={}
        for value in shares:
            try:
                price=(lookup(value))["price"]
                lookup_dict[value]=(price)
                totalsharevalue[value] = '{:.2f}'.format(float(price) * float(shares[value]))

               
            except:
                return apology("Appears there's no internet connection to fetch Stock prices")
        return render_template("portfolio.html",cash=round(cash,2),name=name,shares=shares,shareprice=lookup_dict,totalsharevalue=totalsharevalue)
    else:
        totalsharevalue=[{'date': 'N/A', 'time': 'N/A', 'transaction_type': 'N/A', 'amount': 'N/A', 'symbol': 'N/A', 'shares': 'No Shares'}]
        lookup_dict="N/A"
        shares={}
        return render_template("portfolio.html",cash=round(cash,2),name=name,shares=shares,shareprice=lookup_dict,totalsharevalue=totalsharevalue)




@app.route("/buy", methods=[ "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method=="POST":
            symbol=request.form.get("symbol")
            shares=request.form.get("shares")
            if not symbol or not shares:
                flash("symbol and shares are required")#flash and redirect to same page
                return redirect("/quote")


            try:
                if int(shares)<=0:
                    flash("number of shares must be at least 1")
                    return redirect("/")
                shares=float(shares)
                stockdetails=lookup(symbol)
                price=float(stockdetails["price"])*shares
                user_id = session.get("user_id")
                cash=(db.execute("SELECT cash FROM users WHERE id=?",user_id))[0]["cash"]
                balance=cash-price
                current_datetimen = datetime.now()
                current_datetime = current_datetimen.astimezone(pytz.timezone('Africa/Johannesburg'))
                date= current_datetime.strftime("%Y-%m-%d")
                time = current_datetime.strftime("%H:%M:%S")
                
                if price>cash:
                    flash("insufficient Balance, Please recharge your account")#flash and redirect to same page
                    return redirect("/")
                else:
                    db.execute("INSERT INTO transactions (user_id, date, time, transaction_type, amount,symbol,shares) VALUES (?,?,?,?,?,?,?)",user_id,date,time,"Buy",price,stockdetails['symbol'],shares)
                    db.execute("UPDATE users SET cash = ? WHERE id = ?", balance, user_id)


            except:
                
                flash("Stock not found/shares not greater than 0")
                return redirect("/")
            else:
                return render_template("bought.html",price=round(price,2),shares=round(shares,2),symbol=symbol,cash=round(cash,2),balance=round(balance,2))


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session.get("user_id")
    history=db.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY date DESC,time DESC",user_id)
    return render_template('history.html',history=history)

@app.route("/reset",methods=['GET','POST'])
@login_required
def reset():
    if request.method=="GET":
        return render_template("resetPasswordUsername.html")
    elif request.method=="POST":
        rows = db.execute("SELECT * FROM users WHERE id=?",session.get("user_id"))
        print("ror",rows)
        if  request.form.get("currentPassword") and check_password_hash(rows[0]["hash"], request.form.get("currentPassword")):
            if request.form.get('newUsername') and request.form.get("newPassword"):
                db.execute("UPDATE users SET username=?, hash=? WHERE id=?",request.form.get('newUsername'),generate_password_hash(request.form.get("newPassword")),session.get("user_id"))
                flash("Password & Username have been reset")
                return redirect('/')
            elif request.form.get('newUsername'):
                db.execute("UPDATE users SET username=? WHERE id=?",request.form.get('newUsername'),session.get("user_id"))
                flash("username has been reset")
                return redirect("/")
            elif request.form.get('newPassword'):
                db.execute("UPDATE users SET hash=? WHERE id=?",generate_password_hash(request.form.get("newPassword")),session.get("user_id"))
                flash("Password has been reset")
                return redirect("/")
        else:
            flash("failed to reset anything, incorrect password")
            return redirect("/")
          

        
        
       
    
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)#flash and redirect to same page

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)#flash and redirect to same page

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]


        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=[ "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method=="POST":
        symbol=request.form.get("symbol")
        try:
            user_id = session.get("user_id")
            cash=(db.execute("SELECT cash FROM users WHERE id=?",user_id))[0]["cash"]
            stockDetails=lookup(symbol)
            return render_template("quoted.html",stockprice=usd(stockDetails["price"]),stocksymbol=stockDetails["symbol"],cash=round(cash,2))
        except:
            flash("appears there is no input or symbol not recognized")#flash and redirect to same page
            return redirect("/")
        


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method=="GET":
        return render_template("register.html")
    
    if request.method=="POST":
        username=request.form.get("username")
        password=request.form.get("password")
        confirm=request.form.get("confirmation")
        if not username or not password:
            return apology("authentication failed. username/password not provided",403)
        if not db.execute('SELECT username FROM users WHERE username = ?', (username))==[] :
             return apology("username already exists")#flash and redirect to same page

        else:
            if password==confirm:
                hashed_password=generate_password_hash(password)
                db.execute("INSERT INTO users (username,hash) VALUES (?,?)",username,hashed_password)
                flash("!!you are Registered!!")
                return redirect("/login") 
            else:
                return apology("passwords don't match")



@app.route("/sell", methods=["GET", "POST","PUT"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method=="GET":
        symbol=request.args.get('symbol')
        session['symbol'] = symbol
        return render_template("sell.html",symbol=symbol)
    elif request.method=="POST":
        symbol=session.get("symbol")
        user_id = session.get("user_id")
        shares=db.execute("SELECT SUM(CASE WHEN transaction_type = 'Sell' THEN -1 * shares ELSE shares END) AS sumofshare FROM transactions WHERE  user_id=? AND symbol=?",user_id,symbol)[0]["sumofshare"]
        sellShares=int(request.form.get("sellShares"))
     
        if int(sellShares)<=int(shares):
            try:
                shares=int(shares)-int(sellShares)
            
                cash=(db.execute("SELECT cash FROM users WHERE id=?",user_id))[0]["cash"]
                stockdetails=lookup(symbol)
                price=float(stockdetails["price"])*sellShares
                balance=cash+price
                current_datetimen = datetime.now()
                current_datetime = current_datetimen.astimezone(pytz.timezone('Africa/Johannesburg'))
                date= current_datetime.strftime("%Y-%m-%d")
                time = current_datetime.strftime("%H:%M:%S")
            except:
                pass
            else:
                db.execute("INSERT INTO transactions (user_id, date, time, transaction_type, amount,symbol,shares) VALUES (?,?,?,?,?,?,?)",user_id,date,time,"Sell",price,stockdetails['symbol'],sellShares)
                db.execute("UPDATE users SET cash = ? WHERE id = ?", balance, user_id)
            
            flash(f"You've successfully sold {sellShares} shares of {symbol}")

            return redirect("/")
        else:
            flash("transaction unsuccessful, you are attempting to sell more shares then you own")
            return redirect("/")

    



@app.route("/deposit",methods=['GET','POST'])
@login_required
def deposit():
    if request.method=='GET':
        return render_template("DepositWithdraw.html")
    elif request.method=="POST":
        user_id = session.get("user_id")
        deposit=(request.form.get("deposit"))
        cash=(db.execute("SELECT cash FROM users WHERE id=?",user_id))[0]["cash"]
        cash=float(cash)+float(deposit)
        if deposit.isnumeric():
            db.execute("UPDATE users SET cash=? WHERE id=?",cash,user_id)
            current_datetimen = datetime.now()
            current_datetime = current_datetimen.astimezone(pytz.timezone('Africa/Johannesburg'))
            date= current_datetime.strftime("%Y-%m-%d")
            time = current_datetime.strftime("%H:%M:%S")
            db.execute("INSERT INTO transactions (user_id, date, time, transaction_type, amount,symbol,shares) VALUES (?,?,?,?,?,?,?)",user_id,date,time,"deposit",deposit,"N/A","N/A")
            flash(f"Succesfully deposited ${deposit} into your account",'{:.2f}'.format(float(deposit)))
            return redirect("/")
        else:
            flash("sorry buddy, input must be number")
            return redirect("/")
        
    
  
@app.route("/withdraw",methods=['POST'])
@login_required
def withdraw():
    if request.method=='POST':
        user_id = session.get("user_id")
        withdrawal=float(request.form.get("withdrawal"))
        cash=(db.execute("SELECT cash FROM users WHERE id=?",user_id))[0]["cash"]
        try:
            if float(cash)>=float(withdrawal):
                cash=float(cash)-float(withdrawal)
                db.execute("UPDATE users SET cash=? WHERE id=?",cash,user_id)
                current_datetimen = datetime.now()
                current_datetime = current_datetimen.astimezone(pytz.timezone('Africa/Johannesburg'))
                date= current_datetime.strftime("%Y-%m-%d")
                time = current_datetime.strftime("%H:%M:%S")
                db.execute("INSERT INTO transactions (user_id, date, time, transaction_type, amount,symbol,shares) VALUES (?,?,?,?,?,?,?)",user_id,date,time,"withdrawal",withdrawal,"N/A","N/A")
                flash(f"${withdrawal} was successfully Withdrew",'{:.2f}'.format(float(withdrawal)))
                return redirect("/")
            else:
                flash("transaction failed,your withdrawal amount exceeds available funds")
                return redirect("/")
        except:
            flash("sorry buddy, input must be number")
            return redirect("/")

        

       