from flask import render_template,request, flash, jsonify,redirect,url_for, Flask
import uuid
import jwt
import hashlib

import os
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

import time
from datetime import datetime, timedelta
from pymongo import MongoClient, DESCENDING

# client = MongoClient(
#     "mongodb+srv://ahmadlutfi606:wolfattax@cluster0.xctxali.mongodb.net/?retryWrites=true&w=majority"
# )
# db = client.uangku

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")

client = MongoClient(MONGODB_URI)

db = client[DB_NAME]

SECRET_KEY = "SEEKER"
TOKEN_KEY = "mytoken"

app = Flask(__name__)


@app.route('/sign-up', methods=['GET','POST'])
def sign_up():
    if request.method == 'POST':
        theId = f"{uuid.uuid1()}"
        username_receive = request.form["username"]        
        username_info = db.user.find_one({"username": username_receive})
        password_receive = request.form["password"]
        confirm_password_receive = request.form["confirm_password"]

        if username_info:
            return redirect(url_for("sign_up", msg="Username Sudah Terdaftar"))
        if len(password_receive) < 8:
            return redirect(url_for("sign_up", msg="Password Terlalu Pendek"))
        if password_receive != confirm_password_receive:
            return redirect(url_for("sign_up", msg="Password Tidak valid"))
        
        password_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
        doc = {
            "uuid": theId,
            "username": username_receive,           
            "password": password_hash,         
        }
        db.user.insert_one(doc)

        return redirect(url_for("sign_in", msg="Silahkan Login"))
        
    msg = request.args.get("msg")
    return render_template("auth/sign_up.html", msg=msg)


@app.route('/sign-in', methods=['GET','POST'])
def sign_in():
    # msg = request.args.get("msg")
    # return render_template("auth/sign_in.html", msg=msg)
    if request.method == "POST":
        username_receive = request.form["username_give"]
        password_receive = request.form["password_give"]
        pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
        
        result = db.user.find_one(
            {
                "username": username_receive,
                "password": pw_hash,
            }
        )
        if result:
            payload = {
                "id": username_receive,                                
                "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
            }
            token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

            return jsonify({"result": "success", "token": token})

        else:
            return jsonify(
                {
                    "result": "fail",
                    "msg": "Email atau password salah",
                }
            )

    token_receive = request.cookies.get(TOKEN_KEY)
    # token_receive = request.cookies.get("mytoken")
    if token_receive:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])       
        return redirect(url_for("dashboard"))
    msg = request.args.get("msg")
    return render_template("auth/sign_in.html", msg=msg)



@app.route("/")
def home():        
    return render_template("index.html")
        
    

@app.route("/dashboard")
def dashboard():    
    token_receive = request.cookies.get(TOKEN_KEY)
    # token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.user.find_one({"username": payload["id"]})
        if user_info:

            moneyku = db.money.find_one({"user": user_info['uuid']}, {"_id": False});            
            if moneyku is None:
                uangku = 0
            else:
                moneyku = db.money.find({"user": user_info['uuid']}, {"_id": False}).sort("seconds", -1);
                uangku = moneyku[0]['saldo_update']
            thelist = (
                db.money.find(
                   {"user": user_info['uuid']}, {"_id": False}
                )
                .sort("_id", -1)
            )
            output = []
            for i in thelist:
                output.append(i)
            return render_template("dashboard.html",output=output,uangku=uangku)
        return redirect(url_for("sign_in"))

    except jwt.ExpiredSignatureError:
        return redirect(url_for("sign_in", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("sign_in", msg="There was problem logging you in"))


@app.template_filter()
def format_money(value):
    if value < 0:
        formatted_val = f"-Rp{-value:,.0f}".replace(",", ".")
    else:
        formatted_val = f"Rp{value:,.0f}".replace(",", ".")
    return formatted_val
  
@app.route("/api/save", methods=["POST"])
def save():
    token_receive = request.cookies.get(TOKEN_KEY)
    # token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.user.find_one({"username": payload["id"]})
        if user_info:
            uang_receive = int(request.form["uang_give"])
            deskripsi_receive = request.form["deskripsi_give"]
            options_receive = request.form["options_give"]
            option =  "text-success" if options_receive == "tambah" else "text-danger"       
            uang =  f"Rp{uang_receive:,.0f}".replace(",", ".") if options_receive == "tambah" else f"-Rp{uang_receive:,.0f}".replace(",", ".")
            seconds = time.time()

            moneyku = db.money.find_one({"user": user_info['uuid']}, {"_id": False});            
            if moneyku is None:                 
                update = 0+uang_receive if options_receive == "tambah" else 0-uang_receive 
                doc = {
                    "user": user_info['uuid'],
                    "saldo_awal": 0,
                    "saldo_update": update,
                    "uang": uang,
                    "deskripsi": deskripsi_receive,
                    "options": option,
                    "seconds": seconds,
                    "tanggal": datetime.now().strftime("%d/%m/%Y - %H:%M"),
                }
                db.money.insert_one(doc)
            else: 
                moneyku = db.money.find({"user": user_info['uuid']}, {"_id": False}).sort("seconds", -1);     
                # print(moneyku)

                update = moneyku[0]['saldo_update']+uang_receive if options_receive == "tambah" else moneyku[0]['saldo_update']-uang_receive 
                doc = {
                    "user": user_info['uuid'],
                    "saldo_awal": moneyku[0]['saldo_update'],
                    "saldo_update": update,
                    "uang": uang,
                    "deskripsi": deskripsi_receive,
                    "options": option,
                    "seconds": seconds,
                    "tanggal": datetime.now().strftime("%d/%m/%Y - %H:%M"),
                }
                db.money.insert_one(doc)
            return jsonify({"result": "success", "msg": f"Berhasil"})

        return redirect(url_for("sign_in"))

    except jwt.ExpiredSignatureError:
        return redirect(url_for("sign_in", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("sign_in", msg="There was problem logging you in"))
    

if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
