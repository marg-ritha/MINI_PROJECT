from flask import Flask, request,render_template,session,redirect,url_for
import mysql.connector
import bcrypt

app = Flask(__name__)

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="mysql@Marg27",
    database="virtual_bus_pass_system"
)
cursor = db.cursor()

def insert_user(register_number, full_name, email, password):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    if register_number.startswith("STU"):
        table = "students"
    elif register_number.startswith("ADM"):
        table = "admins"
    elif register_number.startswith("SEC"):
        table = "security"
    else:
        return "Invalid register number format!!"

    query = f"INSERT INTO {table} (register_number, full_name, email, password) VALUES (%s, %s, %s, %s)"
    values = (register_number, full_name, email, hashed_password)
    
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
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        print(f"Received: {register_no}, {full_name}, {email}, {password},{confirm_password}")

        if not all([register_no, full_name, email, password,confirm_password]):
            print("Error: Missing fields")
            return render_template("newuser.html", error="All fields are required!!")
        if password!=confirm_password:
            return render_template("newuser.html", error="Passwords do not match!!")

        result = insert_user(register_no, full_name, email, password)
        print(f"DB Response: {result}") 

        if "User registered" in result:
            return render_template("register.html", message=result)
        else:
            return render_template("newuser.html",error=result)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        register_number = request.form.get("register_number")
        password = request.form.get("password")

        if not register_number or not password:
            return render_template("login.html", error="All fields are required")

        if register_number.startswith("STU"):
            table = "students"
            redirect_page = "students.html"
        elif register_number.startswith("ADM"):
            table = "admins"
            redirect_page = "admin.html"
        elif register_number.startswith("SEC"):
            table = "security"
            redirect_page = "security.html"
        else:
            return render_template("login.html", error="Invalid registration number format!!")

        query = f"SELECT password FROM {table} WHERE register_number = %s"
        cursor.execute(query, (register_number,))
        result = cursor.fetchone()

        if result is None:
            return render_template("login.html", error="User not found")

        hashed_password = result[0]
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
            #session["user"] = register_number
            return redirect(url_for(redirect_page.split(".")[0]))
        else:
            return render_template("login.html", error="Invalid password!!")

    return render_template("login.html")

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True,port=8000)
