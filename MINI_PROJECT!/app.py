from flask import Flask, request,render_template,session,redirect,url_for,flash,jsonify
import mysql.connector
import bcrypt
import os
app = Flask(__name__)
app.secret_key = os.urandom(24)
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="mysql@Marg27",
    database="virtual_bus_pass_system"
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
                if status.lower() != "enabled":  # ✅ Check if student is enabled
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
    try:
        cursor.execute("SELECT bus_destination, drop_off_locations, fare_per_day FROM bus_info")
        buses = cursor.fetchall()
        bus_data = {}
        for destination, locations, fares in buses:
            locations_list = locations.strip('{}').split(',')
            fares_list = [int(f) for f in fares.strip('{}').split(',')]
            bus_data[destination] = {
                "locations": locations_list,
                "fares": fares_list
            }
        return render_template("dayscholar.html", bus_data=bus_data)
    except mysql.connector.Error as e:
        flash(f"Error retrieving bus information: {e}", "error")
        return render_template("dayscholar.html", bus_data={})

@app.route('/get_bus_info')
def get_bus_info():
    if "user" not in session:
        return jsonify({"error": "Unauthorized access"}), 401
    try:
        cursor.execute("SELECT bus_destination, drop_off_locations, fare_per_day FROM bus_info")
        buses = cursor.fetchall()
        bus_data = {}
        for destination, locations, fares in buses:
            # Convert string representations to lists
            locations_list = [loc.strip() for loc in locations.strip('{}').split(',')]
            fares_list = [int(f.strip()) for f in fares.strip('{}').split(',')]
            bus_data[destination] = {
                "locations": locations_list,
                "fares": fares_list
            }
        return jsonify(bus_data)
    except Exception as e:
        app.logger.error(f"Error fetching bus info: {e}")
        return jsonify({"error": str(e)}), 500
@app.route('/proceed_to_payment_hosteller', methods=['POST'])
def proceed_to_payment_hosteller():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 403

    selected_bus_id = request.form.get("selected_bus")
    if not selected_bus_id:
        return jsonify({"error": "Bus ID is missing"}), 400

    try:
        # Update available seats atomically
        cursor.execute("""
            UPDATE bus_info 
            SET available_seats = available_seats - 1 
            WHERE bus_id = %s AND available_seats > 0
        """, (selected_bus_id,))
        db.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "No available seats left"}), 409

        # Retrieve updated seat count
        cursor.execute("SELECT available_seats FROM bus_info WHERE bus_id = %s", (selected_bus_id,))
        updated_seats = cursor.fetchone()[0]

        session["selected_bus_id"] = selected_bus_id
        return jsonify({"updated_seats": updated_seats})

    except mysql.connector.Error as e:
        app.logger.error(f"Database error: {e}")
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({"error": f"Unexpected error: {e}"}), 500

'''@app.route('/proceed_to_payment_hosteller', methods=['POST'])
def proceed_to_payment_hosteller():
    selected_bus_id = request.form.get("selected_bus")
    if not selected_bus_id:
        flash("Please select a bus before proceeding to payment.", "error")
        return redirect(url_for("hosteller"))

    try:
        cursor.execute("UPDATE bus_info SET available_seats = available_seats - 1 WHERE bus_id = %s AND available_seats > 0", (selected_bus_id,))
        db.commit()

        if cursor.rowcount == 0:
            flash("No available seats left for the selected bus.", "error")
            return redirect(url_for("hosteller"))

        session["selected_bus_id"] = selected_bus_id
        flash("Seat reserved successfully. Proceeding to payment.", "success")

    except mysql.connector.Error as e:
        flash(f"Error updating available seats: {e}", "error")
        return redirect(url_for("hosteller"))

    return redirect(url_for('payment'))
'''
@app.route('/proceed_to_payment_dayscholar', methods=['POST'])
def proceed_to_payment_dayscholar():
    session["selected_bus_id"] = request.form.get("selectedBus")
    flash("Proceeding to payment for Dayscholar.", "success")
    return redirect(url_for('payment'))


@app.route('/payment')
def payment():
    return render_template('payment.html')

@app.route('/hosteller')
def hosteller():
    if "user" not in session:
        return redirect(url_for("login"))
    try:
        cursor.execute("SELECT bus_id, bus_destination, total_seats, available_seats FROM bus_info")
        buses = cursor.fetchall()
    except mysql.connector.Error as e:
        flash(f"Error retrieving bus information: {e}", "error")
        buses = []
    return render_template("hosteller.html", buses=buses)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True,port=8000)
