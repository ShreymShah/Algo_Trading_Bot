from flask import Flask, render_template, request, redirect, url_for, flash
import time as t
import threading
from pya3 import *
import mysql.connector

db = mysql.connector.connect(host="", user="", passwd="", database="")
mycursor = db.cursor()
app = Flask(__name__,template_folder='template')

username_api = {}
login_today = False
for_threads = {}
app.secret_key = "DONT"
@app.route("/")
def home():

    return render_template('first_page.html')

@app.route("/addaccount", methods=["POST", "GET"])
def add_account():
    if request.method == "POST":
        username = request.form["Username"]
        api_key = request.form["API Key"]
        username_api[username] = api_key
        mycursor.execute("INSERT INTO username_apikey (username, api_key) VALUES (%s,%s)", (username, api_key))
        db.commit()
        flash("Account Added !")
        return redirect(url_for("add_account"))
    else:
        return render_template('add_account.html')


@app.route('/accounts')
def accounts():
    if login_today:
        msg = "Login Successfull"
    else:
        msg = "Login Not Done"
    username_api = {}
    mycursor.execute("SELECT * from username_apikey")
    for x in mycursor:
        username_api[x[0]] = x[1]
    return render_template('accounts.html',username = username_api)

@app.route('/login/<keyy>/<value>')
def login(keyy,value):
    alice = Aliceblue(user_id=keyy, api_key=value)
    aliceblue_Res = alice.get_session_id()
    print(aliceblue_Res)
    try :
        a = aliceblue_Res['sessionID']
        login_success = True

    except:
        login_success = False

    username_api = {}
    mycursor.execute("SELECT * from username_apikey")
    for x in mycursor:
        username_api[x[0]] = x[1]

    if login_success:
        flash("Login Successfull !")
        return render_template('accounts.html',username = username_api)
    else:
        flash("Login UNSUCCESSFULL, check !")
        return redirect(url_for('accounts'))


@app.route('/delete_account/<keyy>')
def delete_account(keyy):
    mycursor.execute(f"DELETE FROM username_apikey WHERE username = '{keyy}' ")
    db.commit()
    flash("Deleted Account !")
    username_api = {}
    mycursor.execute("SELECT * from username_apikey")
    for x in mycursor:
        username_api[x[0]] = x[1]
    return render_template('accounts.html',username = username_api)

@app.route('/delete_strategy/<symbol>')
def delete_strategy(symbol):
    mycursor.execute(f"DELETE FROM strategy WHERE symbol = '{symbol}' ")
    db.commit()
    flash("Deleted Strategy!")
    return redirect(url_for('run_strategy'))

@app.route('/addstrategy', methods=["POST", "GET"])
def add_strategy():
    username_api = {}
    mycursor.execute("SELECT * from username_apikey")
    for x in mycursor:
        username_api[x[0]] = x[1]

    if request.method == "POST":
        symbol = request.form["Script Symbol"]
        qty = request.form["Quantity"]
        buy_above = request.form["Buy Above"]
        target = request.form["Target"]
        sl = request.form["Stop Loss"]
        acc = request.form["Account"]
        mycursor.execute("INSERT INTO strategy (symbol, buy_above, qty, sl, target, username) VALUES(%s,%s,%s,%s,%s,%s)",(symbol, buy_above, qty, sl, target, acc))
        db.commit()
        flash("Strategy Added!")
        return redirect(url_for("add_strategy"))

    else:
        return render_template('add_strategy.html',username = username_api)

@app.route('/runstrategy')
def run_strategy():
    strategies = {}
    mycursor.execute("SELECT * from strategy")
    for x in mycursor:
        strategies[x[0]] = [x[1],x[2],x[3],x[4],x[5]]

    return render_template('run_strategy.html',strategy=strategies)

@app.route('/run/<symbol>')
def run(symbol):
    mycursor.execute(f"SELECT username FROM strategy WHERE symbol='{symbol}'")
    for x in mycursor:
        params = x
    t1 = threading.Thread(target=mainn, args=(symbol, params[0],))
    t1.start()
    flash("Strategy is RUNNING!")
    return redirect(url_for('run_strategy'))


@app.route('/stop/<symbol>')
def stop(symbol):
    for_threads[symbol] = True
    flash("Strategy STOPPED !")
    return redirect(url_for('run_strategy'))


@app.route('/edit/<symboll>', methods=["POST", "GET"])
def edit(symboll):
    username_api = {}
    mycursor.execute("SELECT * from username_apikey")
    for x in mycursor:
        username_api[x[0]] = x[1]

    strategies = {}
    mycursor.execute("SELECT * from strategy")
    for x in mycursor:
        strategies[x[0]] = [x[1],x[2],x[3],x[4],x[5]]

    if request.method == "POST":
        symbol = request.form["Script Symbol"]
        qty = request.form["Quantity"]
        buy_above = request.form["Buy Above"]
        target = request.form["Target"]
        sl = request.form["Stop Loss"]
        acc = request.form["Account"]
        mycursor.execute(f"UPDATE strategy SET symbol='{symbol}', sl = {sl}, qty={qty},buy_above={buy_above},target={target},username='{acc}' WHERE symbol='{symboll}'")
        db.commit()
        return redirect(url_for("home"))

    else:
        return render_template('edit.html', username=username_api, values=strategies[symboll], symbol=symboll)

def mainn(symbol,acc):
    mycursor.execute(f"SELECT api_key FROM username_apikey WHERE username='{acc}'")
    for x in mycursor:
        api_key = x[0]

    alice = Aliceblue(user_id=acc, api_key=api_key)
    aliceblue_Res = alice.get_session_id()
    print(aliceblue_Res)
    try :
        a = aliceblue_Res['sessionID']
        login_success_ = True
    except:
        login_success_ = False
    buy_complete = False
    if login_success_:
        for_threads[symbol] = False
        while True:
            ins = alice.get_instrument_by_symbol("NSE", symbol)
            mycursor.execute(f"SELECT target,sl,qty,buy_above FROM strategy WHERE symbol='{symbol}'")
            x = mycursor.fetchall()[0]
            target = x[0]
            sl = x[1]
            qty = x[2]
            buy_above = x[3]

            if for_threads[symbol] == True:
                break

            ltp = float(alice.get_scrip_info(ins).get("Ltp"))

            if ltp >= buy_above and buy_complete==False:
                PlaceBuyOrder(alice, ins, qty)
                buy_complete = True

            if buy_complete == True:
                if ltp >=target or ltp<=sl:
                    PlaceSellOrder(alice,ins,qty)
                    break
            t.sleep(20)


def PlaceBuyOrder(alice, ins, qty):
    res_2 = alice.place_order(transaction_type=TransactionType.Buy,
                            instrument=ins,
                            quantity=qty,
                            order_type=OrderType.Market,
                            product_type=ProductType.Delivery,
                            price=0.0,
                            trigger_price=None,
                            stop_loss=None,
                            square_off=None,
                            trailing_sl=None,
                            is_amo=False,
                            order_tag='order1')

def PlaceSellOrder(alice, ins, qty):
    res_1 = alice.place_order(transaction_type=TransactionType.Sell,
                            instrument=ins,
                            quantity=qty,
                            order_type=OrderType.Market,
                            product_type=ProductType.Delivery,
                            price=0.0,
                            trigger_price=None,
                            stop_loss=None,
                            square_off=None,
                            trailing_sl=None,
                            is_amo=False,
                            order_tag='order1')


if __name__ == '__main__':
    app.run(debug=True)


