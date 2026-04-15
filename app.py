from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import random
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
con = mysql.connector.connect(
    host="localhost",
    user="root",
    password="171004",
    database="notesdb"
)

otp_store = {}

# ---------------- EMAIL OTP ----------------
def send_otp(email, otp):
    sender = "narendralenka553@gmail.com"
    password = "ochp jzwg ugwi ebbz"

    msg = MIMEText(f"Your OTP is {otp}")
    msg['Subject'] = "Password Reset OTP"
    msg['From'] = sender
    msg['To'] = email

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender, password)
    server.send_message(msg)
    server.quit()


# ---------------- LOGIN ----------------
@app.route('/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = con.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            flash("Login successful!", "success")
            return redirect('/dashboard')
        else:
            flash("Invalid username or password", "danger")
            return redirect('/')

    return render_template("login.html")


# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        cursor = con.cursor()
        cursor.execute(
            "INSERT INTO users(username,email,password) VALUES(%s,%s,%s)",
            (username,email,password)
        )
        con.commit()

        flash("Registration successful! Please login.", "success")
        return redirect('/')

    return render_template("register.html")


# ---------------- DASHBOARD (FIXED SEARCH) ----------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')

    cursor = con.cursor(dictionary=True)

    search = request.args.get('search')   # ✅ FIXED

    if search:
        query = f"%{search}%"
        cursor.execute(
            "SELECT * FROM notes WHERE user_id=%s AND (LOWER(title) LIKE LOWER(%s)) ORDER BY id DESC",
            (session['user_id'], query)
        )
    else:
        cursor.execute(
            "SELECT * FROM notes WHERE user_id=%s ORDER BY id DESC",
            (session['user_id'],)
        )

    notes = cursor.fetchall()

    return render_template("dashboard.html", notes=notes)


# ---------------- ADD NOTE ----------------
@app.route('/addnote', methods=['GET','POST'])
def addnote():
    if 'user_id' not in session:
        flash("Please login first!", "warning")
        return redirect('/')

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        cursor = con.cursor()
        cursor.execute(
            "INSERT INTO notes(title,content,created_at,user_id) VALUES(%s,%s,NOW(),%s)",
            (title, content, session['user_id'])
        )
        con.commit()
        cursor.close()

        flash("Note added successfully!", "success")
        return redirect('/dashboard')

    return render_template("addnote.html")


# ---------------- VIEW ALL NOTES ----------------
@app.route('/viewall')
def viewall():
    if 'user_id' not in session:
        flash("Please login first!", "warning")
        return redirect('/')

    cursor = con.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM notes WHERE user_id=%s",
        (session['user_id'],)
    )
    notes = cursor.fetchall()

    return render_template("viewall.html", notes=notes)


# ---------------- VIEW ONE NOTE ----------------
@app.route('/viewnotes/<int:id>')
def viewnote(id):
    cursor = con.cursor(dictionary=True)
    cursor.execute("SELECT * FROM notes WHERE id=%s", (id,))
    note = cursor.fetchone()

    return render_template("viewnote.html", note=note)


# ---------------- UPDATE NOTE ----------------
@app.route('/updatenote/<int:id>', methods=['GET','POST'])
def updatenote(id):
    cursor = con.cursor(dictionary=True)

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        cursor.execute(
            "UPDATE notes SET title=%s, content=%s WHERE id=%s",
            (title, content, id)
        )
        con.commit()

        flash("Note updated successfully!", "info")
        return redirect('/viewall')

    cursor.execute("SELECT * FROM notes WHERE id=%s", (id,))
    note = cursor.fetchone()

    return render_template("edit.html", note=note)


# ---------------- DELETE NOTE ----------------
@app.route('/deletenote/<int:id>')
def deletenote(id):
    cursor = con.cursor()
    cursor.execute("DELETE FROM notes WHERE id=%s", (id,))
    con.commit()

    flash("Note deleted successfully!", "danger")
    return redirect('/viewall')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "info")
    return redirect('/')


# ---------------- FORGOT PASSWORD ----------------
@app.route('/forgot', methods=['GET','POST'])
def forgot():
    if request.method == 'POST':
        email = request.form['email']

        cursor = con.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user:
            otp = random.randint(100000, 999999)
            otp_store[email] = otp

            send_otp(email, otp)

            flash("OTP sent to your email!", "info")
            return redirect(f"/verify_otp?email={email}")
        else:
            flash("Email not registered!", "danger")
            return redirect('/forgot')

    return render_template("forgot.html")


# ---------------- VERIFY OTP ----------------
@app.route('/verify_otp', methods=['GET','POST'])
def verify_otp():
    email = request.args.get('email')

    if request.method == 'POST':
        user_otp = int(request.form['otp'])

        if otp_store.get(email) == user_otp:
            flash("OTP verified successfully!", "success")
            return redirect(f"/reset_password?email={email}")
        else:
            flash("Invalid OTP!", "danger")
            return redirect(f"/verify_otp?email={email}")

    return render_template("otp.html", email=email)


# ---------------- RESET PASSWORD ----------------
@app.route('/reset_password', methods=['GET','POST'])
def reset_password():
    email = request.args.get('email')

    if request.method == 'POST':
        new_password = generate_password_hash(request.form['password'])

        cursor = con.cursor()
        cursor.execute(
            "UPDATE users SET password=%s WHERE email=%s",
            (new_password, email)
        )
        con.commit()

        otp_store.pop(email, None)

        flash("Password updated successfully!", "success")
        return redirect('/')

    return render_template("reset.html")


# ---------------- ABOUT ----------------
@app.route('/about')
def about():
    return render_template("about.html")


# ---------------- CONTACT ----------------
@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        message = request.form["message"]

        body = f"""
New Message

Name: {name}
Email: {email}
Phone: {phone}

Message:
{message}
"""

        msg = MIMEText(body)
        msg["Subject"] = "Contact Form"
        msg["From"] = "narendralenka553@gmial.com"
        msg["To"] = "lenkanarendra536@gmail.com"

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("narendralenka553@gmail.com", "ochp jzwg ugwi ebbz")
        server.send_message(msg)
        server.quit()

        return "Message Sent Successfully"

    return render_template("contact.html")


# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)