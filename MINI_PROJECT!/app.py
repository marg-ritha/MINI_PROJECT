from flask import Flask, request,render_template,session,redirect,url_for,flash
import mysql.connector
import bcrypt
import os
app = Flask(__name__)
app.secret_key = os.urandom(24)
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="your_password_here",
    database="name_of_database"
)
cursor = db.cursor()
admin_id = "ADM/3030/22"
full_name = "Principal"
email = "principal@gmail.com"
password = "principal" 
role = "Super Admin"
hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
cursor.execute("SELECT admin_id FROM admins WHERE admin_id = %s", (admin_id,))
existing_admin = cursor.fetchone()
if not existing_admin:
    query = "INSERT INTO admins (admin_id, full_name, email, password, role) VALUES (%s, %s, %s, %s, %s)"
    values = (admin_id, full_name, email, hashed_password, role)
    try:
        cursor.execute(query, values)
        db.commit()
        print("Super Admin added successfully!")
    except mysql.connector.Error as e:
        print(f"Error inserting Super Admin: {e}")
else:
    print("Super Admin already exists, skipping insertion.")


def insert_user(register_number, full_name, email, password,student_type):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    if register_number.startswith("STU"):
        table = "students"
    elif register_number.startswith("ADM"):
        table = "admins"
    elif register_number.startswith("SEC"):
        table = "security"
    else:
        return "Invalid register number format!!"

    query = f"INSERT INTO {table} (register_number, full_name, email, password,student_type) VALUES (%s, %s, %s, %s,%s)"
    values = (register_number, full_name, email, hashed_password,student_type)
    
    try:
        cursor.execute(query, values)
        db.commit()
        return f"User registered in {table} table"
    except mysql.connector.Error as e:
        return str(e)


@app.route('/newuser', methods=['GET'])
def newuser():
    return render_template("newuser.html")
@app.route('/register',methods=['POST'])
def register():
        register_no = request.form.get("regno")
        full_name = request.form.get("fullname")
        email = request.form.get("email")
        student_type = request.form.get("sttype")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        print(f"Received: {register_no}, {full_name}, {email},{student_type},{password},{confirm_password}")

        if not all([register_no, full_name, email, password,confirm_password,student_type]):
            print("Error: Missing fields")
            return render_template("newuser.html", error="All fields are required!!")
        if password!=confirm_password:
            return render_template("newuser.html", error="Passwords do not match!!")

        result = insert_user(register_no, full_name, email, password,student_type)
        print(f"DB Response: {result}") 

        if "User registered" in result:
            return render_template("register.html", message=result)
        else:
            return render_template("newuser.html",error=result)
@app.route('/login', methods=['GET', 'POST'])
def login():
    role = request.args.get("role", "student")
    if request.method == "POST":
        register_number = request.form.get("register_number")
        password = request.form.get("password")

        if not register_number or not password:
            return render_template("login.html", error="All fields are required",role=role)

        if register_number.startswith("STU"):
            table = "students"
            query = f"SELECT password,student_type,status FROM {table} WHERE register_number = %s"
        elif register_number.startswith("ADM"):
            table = "admins"
            query = f"SELECT password, role FROM {table} WHERE admin_id = %s" 
        elif register_number.startswith("SEC"):
            table = "security"
            query = f"SELECT password FROM {table} WHERE register_number = %s"
        else:
            return render_template("login.html", error="Invalid registration number format!!",role=role)

        cursor.execute(query, (register_number,))
        result = cursor.fetchone()

        if result is None:
            return render_template("login.html", error="User not found",role=role)

        hashed_password= result[0]
        extra_field = result[1] if len(result) > 1 else None
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
            session["user"] = register_number
            if table=='students':
                student_type,status=extra_field,result[2]
                if status.lower() != "enabled":  
                    return render_template("login.html", error="Access Denied! Contact Admins.", role=role)
                if student_type == "Day Scholar":
                    return redirect(url_for("dayscholar"))
                elif student_type == "Hosteller":
                    return redirect(url_for("hosteller"))
            elif table=='admins':
                admin_role = extra_field
                session["admin_role"] = admin_role
                if admin_role == "Super Admin":
                    return redirect(url_for("superadmin"))  
                elif admin_role=='Moderator':
                    return redirect(url_for("moderator")) 
            elif table=='security':
                return redirect(url_for("security_dashboard")) 
            else:
                return render_template("login.html", error="Invalid password!!",role=role)

    return render_template("login.html",role=role)

@app.route('/moderator')
def moderator():
    if "user" not in session or session.get("admin_role") != "Moderator":
        return redirect(url_for("login"))
    return render_template("moderator.html",student=None)

@app.route('/add_moderator', methods=['POST'])
def add_moderator():
    if "user" not in session or session.get("admin_role") != "Super Admin":
        return redirect(url_for("login"))

    admin_id = request.form.get("admin_id")
    full_name = request.form.get("full_name")
    email = request.form.get("email")
    password = request.form.get("password")

    # Hash the password before storing
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        query = "INSERT INTO admins (admin_id, full_name, email, password, role) VALUES (%s, %s, %s, %s, 'Moderator')"
        cursor.execute(query, (admin_id, full_name, email, hashed_password))
        db.commit()
        flash("Moderator added successfully!", "success")
    except mysql.connector.Error as e:
        flash(f"Error adding moderator: {e}", "error")
    return redirect(url_for("superadmin"))
@app.route('/delete_moderator', methods=['POST'])
def delete_moderator():
    if "user" not in session or session.get("admin_role") != "Super Admin":
        return redirect(url_for("login"))

    admin_id = request.form.get("admin_id")

    try:
        cursor.execute("SELECT * FROM admins WHERE admin_id = %s AND role = 'Moderator'", (admin_id,))
        moderator = cursor.fetchone()

        if not moderator:
            flash("Error: Moderator not found!", "error")
        else:
            cursor.execute("DELETE FROM admins WHERE admin_id = %s", (admin_id,))
            db.commit()
            flash("Moderator deleted successfully!", "success")
            return redirect(url_for("superadmin"))
    except mysql.connector.Error as e:
        flash(f"Error deleting moderator: {e}", "error")
    return redirect(url_for("superadmin"))

@app.route('/view_student', methods=['POST'])
def view_student():
    if "user" not in session or session.get("admin_role") != "Moderator":
        return redirect(url_for("login"))

    register_number = request.form.get("register_number")

    try:
        cursor.execute("SELECT register_number, full_name, email, status FROM students WHERE register_number = %s", (register_number,))
        student = cursor.fetchone()

        if not student:
            flash("Error: Student not found!", "error")
            return redirect(url_for("moderator"))

    except mysql.connector.Error as e:
        flash(f"Error retrieving student: {e}", "error")
        return redirect(url_for("moderator"))

    return render_template("moderator.html", student=student)
@app.route('/update_student_status', methods=['POST'])
def update_student_status():
    if "user" not in session or session.get("admin_role") != "Moderator":
        return redirect(url_for("login"))

    register_number = request.form.get("register_number")
    status = request.form.get("status")

    try:
        cursor.execute("SELECT * FROM students WHERE register_number = %s", (register_number,))
        student = cursor.fetchone()

        if not student:
            flash("Error: Student not found!", "error")
        else:
            new_status = "Enabled" if status == "Enable" else "Disabled"
            cursor.execute("UPDATE students SET status = %s WHERE register_number = %s", (new_status, register_number))
            db.commit()
            flash(f"Student account {status}d successfully!", "success")

    except mysql.connector.Error as e:
        flash(f"Error updating student status: {e}", "error")

    return redirect(url_for("moderator"))


@app.route('/superadmin')
def superadmin():
    if "user" not in session or "admin_role" not in session:
        return redirect(url_for("login"))
    cursor.execute("SELECT admin_id, full_name, email, role FROM admins")
    admins = cursor.fetchall()
    return render_template("superadmin.html", admins=admins)

@app.route('/security_dashboard')
def security_dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("security_dashboard.html")

@app.route('/dayscholar')
def dayscholar():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dayscholar.html")

@app.route('/hosteller')
def hosteller():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("hosteller.html")
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True,port=8000)
