import datetime
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    send_file,
)
from collections import defaultdict
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = "SECRET_KEY"
DEFAULT_CATEGORIES = {
    "income": ["Salary 💰", "Investment 📊", "Gift 🎁", "Other"],
    "expense": ["Food 🍔", "Transportation 🚌", "Entertainment 🎮", "Other"],
}


# --- API برای گرفتن دسته‌ها ---
@app.route("/get_categories")
def get_categories():
    type_ = request.args.get("type")
    return jsonify(DEFAULT_CATEGORIES.get(type_, []))


def get_user_transactions(user_id=None):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if user_id:
        cur.execute(
            "SELECT type, category, amount, description, date FROM transactions WHERE user_id=?",
            (user_id,),
        )
    else:
        cur.execute(
            "SELECT type, category, amount, description, date FROM transactions"
        )

    rows = cur.fetchall()
    conn.close()

    transactions = [dict(row) for row in rows]
    return transactions


# ------------------- Database -------------------
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT)"""
    )

    cur.execute(
        """CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    type TEXT,
                    category TEXT,
                    amount INTEGER,
                    description TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id))"""
    )
    conn.commit()
    conn.close()


init_db()


# ------------------- Auth -------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        try:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password),
            )
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except:
            return "Username already exists!"
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        else:
            return "Invalid credentials!"
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ------------------- Dashboard -------------------
@app.route("/")
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_id = session["user_id"]
    conn = get_db_connection()
    trans = conn.execute(
        "SELECT * FROM transactions WHERE user_id=?", (user_id,)
    ).fetchall()
    conn.close()

    income_by_category = defaultdict(int)
    expense_by_category = defaultdict(int)
    monthly_summary = defaultdict(lambda: {"income": 0, "expense": 0})

    total_income = 0
    total_expense = 0

    for t in trans:
        cat = t["category"]
        amt = t["amount"]
        date = datetime.datetime.fromisoformat(t["date"])
        month = date.strftime("%Y-%m")
        monthly_summary[month][t["type"]] += amt

        if t["type"] == "income":
            income_by_category[cat] += amt
            total_income += amt  
        else:
            expense_by_category[cat] += amt
            total_expense += amt 

    return render_template(
        "dashboard.html",
        income_by_category=income_by_category,
        expense_by_category=expense_by_category,
        monthly_summary=monthly_summary,
        total_income=total_income, 
        total_expense=total_expense,  
    )


# ------------------- Transactions -------------------
@app.route("/transactions")
def transactions():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    user_id = session["user_id"]
    trans = conn.execute(
        "SELECT * FROM transactions WHERE user_id=? ORDER BY date DESC", (user_id,)
    ).fetchall()
    conn.close()
    return render_template("transactions.html", transactions=trans)


@app.route("/add_transaction", methods=["GET", "POST"])
def add_transaction():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        user_id = session["user_id"]
        type_ = request.form["type"]
        category = request.form["category"]
        new_cat = request.form.get("new_category", "").strip()
        if category == "Other" and new_cat != "":
            category = new_cat
        elif category == "Other" and new_cat == "":
            category = "Other"
        amount = request.form["amount"]
        description = request.form["description"]
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO transactions (user_id,type,category,amount,description) VALUES (?,?,?,?,?)",
            (user_id, type_, category, amount, description),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("transactions"))
    return render_template("add_transaction.html", categories=DEFAULT_CATEGORIES)


@app.route("/edit_transaction/<int:id>", methods=["GET", "POST"])
def edit_transaction(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    trans = conn.execute(
        "SELECT * FROM transactions WHERE id=? AND user_id=?", (id, session["user_id"])
    ).fetchone()

    if request.method == "POST":
        type_ = request.form["type"]
        category = request.form["category"]
        new_cat = request.form.get("new_category", "").strip()
        if category == "Other" and new_cat != "":
            category = new_cat 
        elif category == "Other" and new_cat == "":
            category = "Other" 
        amount = request.form["amount"]
        description = request.form["description"]

        conn.execute(
            "UPDATE transactions SET type=?, category=?, amount=?, description=? WHERE id=?",
            (type_, category, amount, description, id),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("transactions"))

    conn.close()
    return render_template(
        "edit_transaction.html", trans=trans, categories=DEFAULT_CATEGORIES
    )


@app.route("/delete_transaction/<int:id>")
def delete_transaction(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM transactions WHERE id=? AND user_id=?", (id, session["user_id"])
    )
    conn.commit()
    conn.close()
    return redirect(url_for("transactions"))


@app.route("/export_transactions/<file_type>")
def export_transactions(file_type):
    transactions = get_user_transactions()
    df = pd.DataFrame(transactions)
    df = df[["type", "category", "amount", "description", "date"]]
    df = df.rename(
        columns={
            "type": "Type",
            "category": "Category",
            "amount": "Amount",
            "description": "Description",
            "date": "Date",
        }
    )

    sort_by = request.args.get(
        "sort_by", "date"
    ).capitalize()  
    if sort_by in df.columns:
        df = df.sort_values(by=sort_by)

    if file_type == "csv":
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype="text/csv",
            as_attachment=True,
            download_name="transactions.csv",
        )
    elif file_type == "excel":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Transactions")
        output.seek(0)
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="transactions.xlsx",
        )
    else:
        return "Invalid file type", 400


if __name__ == "__main__":
    app.run(debug=True)
