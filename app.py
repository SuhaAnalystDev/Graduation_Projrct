from flask import Flask, render_template, request, redirect, url_for, session, flash, get_flashed_messages, jsonify
import pymysql
from dotenv import load_dotenv
import re
from werkzeug.security import generate_password_hash, check_password_hash
import base64
import mimetypes
import os
import mdpd
import pandas as pd
from io import StringIO
import shutil
from datetime import datetime
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_wtf import CSRFProtect
import google.generativeai as genai

# API key
api_key = os.environ.get('API_KEY')
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

# Set upload folder (optional)
UPLOAD_FOLDER = 'Uploads_Image'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
load_dotenv()

app = Flask(__name__)
os.environ['FLASK_ENV'] = 'app'
app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF protection for testing
csrf = CSRFProtect(app)
app.secret_key = 'Hthsyr55fgr2sfhdbjs44'


# Email Validation Pattern
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@taibahu\.edu\.sa$")

# Database Connection
def db_connection():
    try:
        conn = pymysql.connect(
            host=os.environ.get('DB_HOST'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            database=os.environ.get('DB_NAME'),
            port=int(os.environ.get('DB_PORT')),
            cursorclass=pymysql.cursors.DictCursor   
        )   
        return conn
    except pymysql.MySQLError as err:
        print("Database connection error:", err)
        return None

def sendEmail(title, subject, message, email):
    me = "badeely.system@gmail.com" 
    password = os.environ.get('EMAIL_PASSWORDE')
    to = email 
    try: 
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = "منصة بدّيلي - " + title 
        msg['To'] = ", ".join(to) 
        msg.attach(MIMEText(message, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server: 
            server.login(me, password)
            server.sendmail(me, to, msg.as_string())  
            server.quit()           
        return
    except Exception as e:
        print(f"Error sending email: {e}")

# Function to encode the image to Base64
def encode_image(image_path):
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "application/octet-stream"
    with open(image_path, "rb") as img:
        base64_str = base64.b64encode(img.read()).decode("utf-8")

    img = {"mime_type": mime_type, "data": base64_str}
    return img

def get_user_student_info(student_id):
    conn = db_connection()
    cursor = conn.cursor()

    sql = """
        SELECT * FROM users WHERE Academic_Number = %s
    """
    cursor.execute(sql, (student_id,))
    user_info = cursor.fetchall()
    
    cursor.close()
    conn.close()

    return user_info

def get_user_advisor_info(email):
    conn = db_connection()
    cursor = conn.cursor()

    sql = """
        SELECT * FROM users WHERE email = %s
    """
    cursor.execute(sql, (email,))
    user_info = cursor.fetchall()
    
    cursor.close()
    conn.close()

    return user_info

# Get Student Courses   
def get_courses(student_id):
    mydb = db_connection()
    if mydb is None:
        return []

    cursor = mydb.cursor()
    query = "SELECT ID, Course_ID, Course_Number, Course_Name FROM student_schedules WHERE Student_ID = %s"
    cursor.execute(query, (student_id,))
    courses = cursor.fetchall()
    cursor.close()
    mydb.close()

    return courses

def get_student_schedule(student_id, course_id, course_number):
    conn = db_connection()

    if conn is None:
        return []

    cursor = conn.cursor()
    query = "SELECT * FROM student_schedules WHERE Student_ID = %s AND (Course_ID != %s OR Course_Number != %s)"

    try:
        cursor.execute(query, (student_id, course_id, course_number))
        rows = cursor.fetchall()
        schedule = []
        for row in rows:
            schedule.append({day: row[day] for day in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"] if row and row[day]})
        return schedule
    except pymysql.MySQLError as err:
        print(f"Database error: {err}")
        return []
    finally:
        cursor.close()
        conn.close()

def check_conflict(time_1, time_2):
    if not time_1 or not time_2 or "-" not in time_1 or "-" not in time_2:  
        return False 
    try:
        start_1, end_1 = map(lambda t: datetime.strptime(t.strip(), "%H:%M"), time_1.split('-'))
        start_2, end_2 = map(lambda t: datetime.strptime(t.strip(), "%H:%M"), time_2.split('-'))
        return start_1 < end_2 and end_1 > start_2
    except ValueError:
        return False

def get_no_conflict_sections(student_id, course_id, course_number, current_section):

    student_schedule = get_student_schedule(student_id, course_id, course_number)

    conn = db_connection()

    if conn is None:
        return []

    cursor = conn.cursor()
    query = "SELECT Section, Sunday, Monday, Tuesday, Wednesday, Thursday FROM time_schedule WHERE Course_ID = %s AND Course_Number = %s AND section != %s"
    cursor.execute(query,(course_id, course_number, current_section))
    sections = cursor.fetchall()
    cursor.close()
    conn.close()

    non_conflicting_sections = []
    for section in sections:
        conflict = False
        if isinstance(student_schedule, list):
            for student_course in student_schedule:
                for day, student_time in student_course.items():
                    if day in section and section[day] and student_time:
                        if check_conflict(student_time, section[day]):
                            conflict = True
                            break
                if conflict:
                    break
        else:
            print("Error: Student schedule is not a list.")
            return []

        if not conflict:
            non_conflicting_sections.append(section["Section"])

    return non_conflicting_sections

def check_request_exists(student_id, course_id, course_number):
    conn = db_connection()
    cursor = conn.cursor()

    sql = """
    SELECT EXISTS (
        SELECT 1 FROM requests_schedule
        WHERE academic_number = %s AND course_id = %s AND course_number = %s
        UNION
        SELECT 1 FROM accepted_requests
        WHERE (student1_id = %s or student1_id = %s or student2_id = %s or student3_id = %s or student4_id = %s or student5_id = %s)  AND course_id = %s AND course_number = %s
    ) AS request_exists;
    """

    cursor.execute(sql, (student_id,course_id, course_number,student_id,student_id,student_id,student_id,student_id,student_id,course_id, course_number))
    result = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    value = result['request_exists']
    
    isExists = False

    if(value == 1):
        isExists = True
    else:
        isExists = False

    return isExists

def filterRequests(course_id, course_number, major, gender, branch='Madinah'):
    try:  
        conn = db_connection()
        cursor = conn.cursor()

        student_emails = []

        query = """
            SELECT rs.Academic_Number, rs.Course_ID, rs.Course_Number, rs.Course_Name, rs.Current_Section, rs.Desired_Section, rs.Academic_advisor_email 
            FROM requests_schedule rs
            WHERE rs.Course_ID = %s 
            AND rs.Course_Number = %s 
            AND rs.Status = 'pending' 
            AND rs.Academic_Number IN (
                SELECT u.Academic_Number FROM users u 
                WHERE u.Major = %s AND u.Gender = %s
            )
        """
        cursor.execute(query, (course_id, course_number, major, gender))
        
        requests_schedule = cursor.fetchall()

        query_1 = """
            SELECT Username, Email
            FROM users 
            WHERE User_type = 'Advisor' AND Major = %s AND Gender = %s AND Branch = %s
        """
        cursor.execute(query_1, (major, gender, branch))

        advising_committee_info = cursor.fetchone()

        if advising_committee_info:
            advisory_committee_name, advisory_committee_email = advising_committee_info
        else:
            advisory_committee_name = None
            advisory_committee_email = None


        request_map = {}

        for student_id, course_id, course_number, course_name, current_section_section, desired_section, advisor_email in requests_schedule:
            key = (course_id, course_number, course_name)
            if key not in request_map:
                request_map[key] = {}
            request_map[key][current_section_section] = (student_id, desired_section, advisor_email)
        

        successful_swaps = []
        visited = set()

        for (course_id, course_number, course_name), section_map in request_map.items():
            for start_section in list(section_map.keys()):
                if start_section in visited:
                    continue

                # Detect circular swaps
                cycles = []
                current_section = start_section

                while current_section in section_map and current_section not in [cycle[4] for cycle in cycles]: 
                    student_id, desired_section, advisor_email = section_map[current_section]
                    cycles.append((student_id, course_id, course_number, course_name, current_section, desired_section, advisor_email))
                    current_section = desired_section

                if 2 <= len(cycles) <= 5 and cycles[0][4] == current_section:
                    successful_swaps.append(cycles)
                    visited.update([cycle[4] for cycle in cycles])

                    matching_students = []
                    for student_data in cycles:
                        matching_students.extend([student_data[0], student_data[4], student_data[5], student_data[6]])

                    while len(matching_students) < 5 * 4: 
                        matching_students.append(None)

                    matching_students.extend([course_id, course_number, course_name, advisory_committee_name, advisory_committee_email, gender, major])
                    

                    query_3 = """
                        SELECT Email FROM users 
                        WHERE academic_number IN ({})
                    """
                    cursor.execute(query_3.format(', '.join(['%s'] * len(cycles))), tuple([student[0] for student in cycles]))
                    emalis_list = cursor.fetchall()
                    student_emails = [email[0] for email in emalis_list]              

                    sql = """
                    INSERT INTO accepted_requests (student1_id, current_section_1, desired_section_1, 
                                                academic_advisor_email_1, student2_id, current_section_2, desired_section_2,
                                                academic_advisor_email_2, student3_id, current_section_3, desired_section_3, 
                                                academic_advisor_email_3, student4_id, current_section_4, desired_section_4, 
                                                academic_advisor_email_4, student5_id, current_section_5, desired_section_5, 
                                                academic_advisor_email_5, course_id, course_number, course_name, advisory_committee_name, 
                                                advisory_committee_email, gender, department) 
                        VALUES ({})
                    """.format(', '.join(['%s'] * (len(matching_students))))
                    
                    cursor.execute(sql, matching_students)
                    
                    # Remove matched students from requests_schedule
                    delete_query = """
                        DELETE FROM requests_schedule 
                        WHERE academic_number IN ({})
                    """
                    cursor.execute(delete_query.format(', '.join(['%s'] * len(cycles))), tuple([student[0] for student in cycles]))


        course_name = requests_schedule[0][3]  
        title = "رسالة إشعار بوجود طلب تبادل مناسب"
        subject = "تم العثور على طلب تبادل متطابق لك"
        msg = f""" 
            <html>
            <body dir="rtl" style="font-family: Arial; text-align: right; color: #000;">
                <p>مرحبًا،</p>

                <p>تم العثور على طالب تتطابق شُعبته مع طلبك في مقرر <strong>{course_name}</strong><br>
                وقد تم إرسال الطلب إلى لجنة الإرشاد الأكاديمي لمراجعته واتخاذ القرار</p>

                <p>بإمكانك متابعة حالة الطلب من خلال صفحة “الطلبات” في حسابك</p>

                <p>نتمنى لك كل التوفيق<br>
                فريق بدّيلي</p>
            </body>
            </html>   
        """          
        if(student_emails):
            sendEmail(title, subject, msg, student_emails)

    except pymysql.MySQLError as err:
        print(f"Database error sub: {err}")
        return jsonify({'error': 'Database error', 'message': str(err)}), 500
    except Exception as e:
        print(f"Unexpected error sub: {e}")
        return jsonify({'error': 'Unexpected error', 'message': str(e)}), 500            
    finally:
        conn.commit()
        cursor.close()
        conn.close()

def get_status_from_db(student_id):
    try:
        conn = db_connection()
        cursor = conn.cursor()

        query = """
        SELECT status, COUNT(*) AS count 
        FROM (
            SELECT status FROM requests_schedule
            WHERE academic_number = %s
            UNION ALL
            SELECT status FROM accepted_requests
            WHERE student1_id = %s or student1_id = %s or student2_id = %s or student3_id = %s or student4_id = %s or student5_id = %s
        ) AS all_requests
        GROUP BY status;
        """

        cursor.execute(query, (student_id,student_id,student_id,student_id,student_id,student_id,student_id))
        rows = cursor.fetchall()

        data = {row['status']: row['count'] for row in rows}
        data['total'] = sum(data.values())

        cursor.close()
        conn.close()

        return data

    except pymysql.MySQLError as err:
        print(f"Error: {err}")
        return {"error": str(err)}

def get_status_ac_from_db(department, gender):
    try:
        conn = db_connection()
        cursor = conn.cursor()

        query = """
            SELECT status, COUNT(*) AS count
            FROM accepted_requests
            WHERE department = %s AND gender = %s
            GROUP BY status;
        """

        cursor.execute(query, (department, gender))
        rows = cursor.fetchall()

        data = {row['status']: row['count'] for row in rows}
        data['total'] = sum(data.values())

        cursor.close()
        conn.close()

        return data

    except pymysql.MySQLError as err:
        print(f"Error: {err}")
        return {"error": str(err)}

def get_student_requests(student_id):
    """Retrieve all requests and their status for a student."""
    conn = db_connection()
    cursor = conn.cursor()

    sql = """
        SELECT request_id, status,note
        FROM requests_schedule
        WHERE academic_number = %s
        UNION
        SELECT match_id, status,note
        FROM accepted_requests
        WHERE student1_id = %s or student1_id = %s or student2_id = %s or student3_id = %s or student4_id = %s or student5_id = %s;
    """

    cursor.execute(sql, (student_id,student_id,student_id,student_id,student_id,student_id,student_id))
    requests = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return requests

def get_accepted_requests(department, gender):
    conn = db_connection()
    cursor = conn.cursor()

    sql = """
        SELECT * FROM accepted_requests WHERE department = %s AND gender = %s
    """

    cursor.execute(sql, (department, gender))
    accepted_requests = cursor.fetchall()
    
    cursor.close()
    conn.close()

    return accepted_requests

def get_request_details_accepted_requests(request_id):
    conn = db_connection()
    cursor = conn.cursor()

    sql = """
        SELECT * FROM accepted_requests WHERE match_id = %s
    """

    cursor.execute(sql, (request_id,))
    accepted_requests = cursor.fetchall()
    
    cursor.close()
    conn.close()

    return accepted_requests

def get_request_details(request_id, student_id):

    conn = db_connection()
    cursor = conn.cursor()

    fetch_rs = """
            SELECT request_id, course_id, course_number, course_name, current_section, desired_section, status, note
            FROM requests_schedule 
            WHERE request_id = %s AND Academic_Number = %s;
        """
    
    params_rs = (request_id, student_id)
    cursor.execute(fetch_rs, params_rs)
    request_details_rs = cursor.fetchall()

    if request_details_rs:
        return request_details_rs 
    
    fetch_ar = """
            SELECT  
                ar.match_id As request_id, ar.course_id, ar.course_number, ar.course_name, ar.status, ar.note,
                CASE
                    WHEN ar.student1_id = %s THEN ar.current_section_1
                    WHEN ar.student2_id = %s THEN ar.current_section_2
                    WHEN ar.student3_id = %s THEN ar.current_section_3
                    WHEN ar.student4_id = %s THEN ar.current_section_4
                    WHEN ar.student5_id = %s THEN ar.current_section_5
                    ELSE NULL
                END AS current_section,
                CASE
                    WHEN ar.student1_id = %s THEN ar.desired_section_1
                    WHEN ar.student2_id = %s THEN ar.desired_section_2
                    WHEN ar.student3_id = %s THEN ar.desired_section_3
                    WHEN ar.student4_id = %s THEN ar.desired_section_4
                    WHEN ar.student5_id = %s THEN ar.desired_section_5
                    ELSE NULL
                END AS desired_section
            FROM accepted_requests ar
            WHERE ar.match_id = %s
            AND %s IN (ar.student1_id, ar.student2_id, ar.student3_id, ar.student4_id, ar.student5_id);
        """
    params_ar = (
        student_id,
        student_id,
        student_id,
        student_id,
        student_id,
        student_id,
        student_id,
        student_id,
        student_id,
        student_id,
        request_id,
        student_id,
    )

    cursor.execute(fetch_ar, params_ar)
    request_details_ar = cursor.fetchall()

    cursor.close()
    conn.close()

    if request_details_ar:
        return request_details_ar

def get_search_result(value, student_id):
    conn = db_connection()
    cursor = conn.cursor()
    query = """
          SELECT rs.request_id AS id FROM requests_schedule rs
          WHERE rs.request_id LIKE %s AND rs.Academic_Number = %s

          UNION

          SELECT ar.match_id AS id FROM accepted_requests ar
          WHERE ar.match_id LIKE %s AND (ar.student1_id = %s or ar.student1_id = %s or ar.student2_id = %s or ar.student3_id = %s or ar.student4_id = %s or ar.student5_id = %s);
    """
    cursor.execute(query, (f'%{value}%', student_id, f'%{value}%',student_id,student_id,student_id,student_id,student_id,student_id))
    result = cursor.fetchall()

    cursor.close()
    conn.close()

    return result

def get_search_result_ac(value, gender, department):
    conn = db_connection()
    cursor = conn.cursor()
    query = """
          SELECT match_id AS id FROM accepted_requests
          WHERE match_id LIKE %s AND gender = %s AND department = %s;
    """
    cursor.execute(query, (f'%{value}%', gender, department))
    result = cursor.fetchall()

    cursor.close()
    conn.close()

    return result

## Main
@app.route('/', endpoint= 'badeely')
def index():
    return render_template('index.html')

@app.route('/login_page', endpoint= 'login_page' )
def loginPage():
    return render_template('login.html')

@app.route('/forgot_password_page', endpoint= 'forgot_password_page')
def forgetPasswordPage():
    return render_template('resetPasword_1.html')

@app.route('/reset_password_page', endpoint='reset_password_page')
def resetPasswordPage():
    return render_template('resetPasword_2.html')
# 
@app.route('/login', methods=['GET', 'POST'], endpoint= 'login')
def login():
    message = None
    category = None
    url = None  

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()


        if user:
            if check_password_hash(user['Password'], password):
                session['username'] = user['Username']
                print(session['username'])
                if(user['User_type'] == 'Student'):
                    session['academic_number'] = user['Academic_Number']
                    session['major'] = user['Major']
                    session['gender'] = user['Gender']

                    message = "تم تسجيل الدخول بنجاح!"
                    category= "success"
                    url = url_for("home")

                elif(user['User_type'] == 'Advisor'): 
                    session['email_ac'] = user['Email']
                    session['gender_ac'] = user['Gender']
                    session['department'] = user['Major']

                    message = "تم تسجيل الدخول بنجاح!"
                    category= "success"
                    url = url_for("home_ac")
                else:
                    message = "تم تسجيل الدخول بنجاح!"
                    category= "success"
                    url = url_for("dashboard")

            else:
                message = "البريد الإلكتروني او كلمة المرور غير صالحة"
                category= "danger"
        else:
            message = "البريد الإلكتروني غير موجود!"
            category= "danger"

    return render_template('login.html', message=message, category=category, url=url)

@app.route('/check_email', methods=['GET', 'POST'], endpoint="check_email")
def checkEmail():
    message = None
    category = None
    url = None

    if request.method == 'POST':
        email = request.form['email']

        conn = db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            session['resetPassword_email'] = email
            url = url_for('reset_password_page')
        else:
            message = "البريد الإلكتروني غير موجود!"
            category = "danger"

    return render_template('resetPasword_1.html', message=message, category=category, url=url)

@app.route('/reset_password', methods=['GET', 'POST'], endpoint="reset_password")
def resetPassword():

    message = None
    category = None
    url = None

    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        email = session['resetPassword_email']

        conn = db_connection()
        cur = conn.cursor()

        # Password match validation
        if password != confirm_password:
            message = "كلمة المرور غير متطابقة!"
            category = "danger"
        
        hashed_password = generate_password_hash(password)

        cur.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_password, email))
        conn.commit()
        cur.close()
        conn.close()

        message = "تم إعادة إنشاء كلمة المرور بنجاح"
        category = "success"
        url = url_for('login')

    return render_template('resetPasword_2.html', message=message, category=category, url=url)

@app.route('/get_username')
def userName():
    username = session['username']
    return jsonify(username = username)

## Students
@app.route('/register_page', endpoint= 'register_page')
def registerPage():
    return render_template('register.html')

@app.route('/imageTool_page', endpoint='imageTool_page')
def imageToolPage():
    edit = request.args.get('edit')
    return render_template('imageTool.html', edit=edit)

@app.route('/home', endpoint= 'home')
def homePage():
    return render_template('home.html')

@app.route('/get_search_results')
def search():
    student_id = session['academic_number']
    request_id = request.args.get('request_id')
    print(request_id)
    data = get_search_result(request_id, student_id)
    return jsonify(data)

@app.route('/profile', endpoint='profile')
def profilePage():
    student_id = session['academic_number']
    info = get_user_student_info(student_id)
    value_translation = {
        'Taibahu':'طيبه',
        'Female': 'أنثى',
        'Male': 'ذكر',
        'Computer Science & Engineering': 'علوم وهندسة الحاسبات',
        'Computer Science': 'علوم الحاسب الآلي',
        'Information Systems': 'نظم المعلومات',
        'Computer Engineering':'هندسة الحاسب الآلي',
        'Cybersecurity':'الأمن السيبراني',
        'Artificial Intelligence and Data Science': 'الذكاء الاصطناعي وعلم البيانات'
    }

    for item in info:
        for key in item:
            if isinstance(item[key], str) and item[key] in value_translation:
                item[key] = value_translation[item[key]]
    return render_template('profile.html', user_info = info)

@app.route("/update_profile", methods=["POST"])
def update_profile():

    conn = db_connection()
    cursor = conn.cursor()

    message = None
    category = None
    url = None      

    value_translation = {
        'طيبه' : 'Taibahu',
        'أنثى' : 'Female',
        'ذكر' : 'Male',
        'علوم وهندسة الحاسبات' : 'Computer Science & Engineering',
        'علوم الحاسب الآلي' : 'Computer Science',
        'نظم المعلومات' : 'Information Systems',
        'هندسة الحاسب الآلي' : 'Computer Engineering',
        'الأمن السيبراني' : 'Cybersecurity',
        'الذكاء الاصطناعي وعلم البيانات' : 'Artificial Intelligence and Data Science'
    }

    academic_number = request.form['academic_number'].strip()
    email = request.form['email'].strip()
    username = request.form['username'].strip()
    gender = value_translation.get(request.form['gender'].strip(), request.form['gender'].strip())
    university = value_translation.get(request.form['university'].strip(),request.form['university'].strip())
    college = value_translation.get(request.form['college'].strip(),request.form['college'].strip())
    major = value_translation.get(request.form['major'].strip(), request.form['major'].strip())
    advisor_email = request.form['academic_advisor_email'].strip()

    student_id = session['academic_number']

    query = """
        UPDATE users SET Academic_Number = %s, Email = %s, Username = %s, Gender = %s, College = %s, 
        University = %s, Major = %s, Academic_advisor_email =%s, Academic_Number_Unique = %s WHERE Academic_Number = %s
    """ 

    cursor.execute(query ,(academic_number, email,username,gender,college,university,major,advisor_email,academic_number,student_id))
    conn.commit()
    cursor.close()
    conn.close()

    message = "تم تحديث الملف الشخصي بنجاح!"
    category = "success"
    url = url_for('home')

    return render_template("profile.html", message=message, category=category, url=url)

@app.route("/switch_sectinon_request_page", endpoint= 'switch_sectinon_request_page')
def switchSectionRequestPage():
    student_id = session['academic_number']
    if not student_id:
        return "Student ID not found", 400

    courses = get_courses(student_id)

    return render_template('switch_section_request.html', courses=courses)

@app.route('/register', methods=['GET', 'POST'], endpoint= 'register')
def register():

    message = None
    category = None
    url = None  

    if request.method == 'POST':
        conn = db_connection()
        cur = conn.cursor()

        try:
            # Get form data and remove unnecessary spaces
            academic_number = request.form['academic_number'].strip()
            email = request.form['email'].strip()
            username = request.form['username'].strip()
            gender = request.form['gender'].strip()
            university_name = request.form['university_name'].strip()
            college = request.form['college'].strip()
            major = request.form['major'].strip()
            branch = request.form['branch'].strip()
            advisor_email = request.form['academic_advisor_email'].strip()
            password = request.form['password']
            confirm_password = request.form['confirm_password']

            # Email validation
            if not EMAIL_PATTERN.match(email):
                message = "تنسيق البريد الإلكتروني غير صالح يجب ان ينتهي @taibahu.edu.sa"
                category = "danger"

            # Password match validation
            if password != confirm_password:
                message = "كلمة المرور غير متطابقة!"
                category = "danger"

            # Check if email already exists
            query_1 = "SELECT * FROM users WHERE email = %s"
            cur.execute(query_1, (email,))
            if cur.fetchone():
                message = "البريد الإلكتروني موجود بالفعل!"
                category = "danger"                

            # Hash password
            hashed_password = generate_password_hash(password)

            # Insert new user
            query_2 = """ 
                INSERT INTO users 
                (User_type, Academic_Number, Email, Username, Gender,College, University, Major, Academic_Advisor_Email, Branch, Password) 
                VALUES ('Student', %s, %s, %s, %s, %s, %s, %s, %s,%s, %s) 
            """
            cur.execute(query_2, (academic_number, email, username, gender, college, university_name, major, advisor_email, branch, hashed_password,))
            conn.commit()

            # Store academic_number in session
            session["academic_number"] = academic_number
            session['username'] = username
            session['major'] = major
            session['gender'] = gender

            message = "تم إنشاء حسابك بنجاح!"
            category = "success" 
            url =  url_for('imageTool_page')

        finally:
            cur.close()
            conn.close()

    return render_template('register.html', message=message, category=category, url=url)
# 
@app.route("/upload", methods=['GET', 'POST'], endpoint="upload")
def user_table():

    message = None
    category = None
    url = None
    arabic_df = None

    if request.method == 'POST':
        if 'image' not in request.files:
            message = "الصورة غير موجودة"
            category = "danger"
            return 

        image = request.files['image']
        if image.filename == '':
            message = "قم باختيار الصورة الصحيحة رجاءً"
            category = "danger"            
            return 

        # save the image
        image_path = os.path.join(UPLOAD_FOLDER, image.filename)
        image.save(image_path)

        # saved image to Base64
        base64_image = encode_image(image_path)

        prompt = """"
                From the image, extract the table data. 

                Focus only on the columns labeled 'رمز', 'رقم', and 'شعبة' only read this columns correctly.

                Rename these columns to Course_ID, Course_Number, and Section, respectively.

                Ensure the output is a Markdown table with the following:
                - No extra columns or rows beyond the specified ones.
                - No null or empty rows.
                - Data in the correct order as it appears in the image, reading from right to left.
                - Only English letters and numbers in the output.

                Provide the extracted data in a Markdown table format.
        """
        response = model.generate_content([base64_image, prompt], stream=False)
        
        markdown_table = response.text
        df_1 = mdpd.from_md(markdown_table)
        
        # Database Query
        mydb = db_connection()
        if mydb is None:
            return "Database connection failed.", 500
        
        cursorObject = mydb.cursor()
        new_df = pd.DataFrame(columns=["Course_ID", "Course_Number", "Course_Name", "Section", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])

        for _, row in df_1.iterrows():
            course_id = row['Course_ID']
            course_number = row['Course_Number']
            section = row['Section']
            
            query = """
                SELECT Course_ID, Course_Number, Course_Name, Section, Sunday, Monday, Tuesday, Wednesday, Thursday
                FROM time_schedule
                WHERE Course_ID = %s AND Course_Number = %s AND Section = %s
            """
            
            cursorObject.execute(query, (course_id, course_number, section))
            result = cursorObject.fetchall()
            
            if result:
                result_df = pd.DataFrame(result, columns=["Course_ID", "Course_Number", "Course_Name", "Section", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"])
                new_df = pd.concat([new_df, result_df], ignore_index=True)
                arabic_df = new_df.copy()
                arabic_df.columns = ["رمز", "رقم", "المادة", "الشعبة", "أحد", "اثنين", "ثلاثاء", "أربعاء", "خميس"]

        cursorObject.close()
        mydb.close()

        session['df'] = new_df.to_csv(index=False)

        

        if os.path.exists(UPLOAD_FOLDER):
            shutil.rmtree(UPLOAD_FOLDER) 
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        return render_template('imageTool.html', message=message, category=category, url=url, 
        df= arabic_df.to_html(classes="table w-100 h-100 mb-0 text-center align-middle table-bordered")  if arabic_df is not None else None)
    
    return render_template('imageTool.html')

@app.route("/save", methods=['POST'], endpoint="save")
def save_table():
    try:
        message = None
        category = None
        url = None 

        if 'df' not in session:
            return "No table data available to save.", 400

        df_csv = session['df']
        df_merged = pd.read_csv(StringIO(df_csv))


        df_merged['Student_ID'] = session['academic_number']

        column_order = ['Student_ID'] + [col for col in df_merged.columns if col != 'Student_ID']
        df_merged = df_merged[column_order]

        expected_columns = ["Student_ID", "Course_ID", "Course_Number", "Course_Name", "Section", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]

        df_merged = df_merged.reindex(columns=expected_columns, fill_value="")
        df_merged = df_merged.fillna("")

        data_to_insert = df_merged.values.tolist()

        for row in data_to_insert:
            if len(row) != len(expected_columns):
                return "Data has incorrect number of values for insertion.", 400

        mydb = db_connection()
        if mydb is None:
            return "Database connection failed.", 500

        cursor = mydb.cursor()
        insert_query = """
        INSERT INTO student_schedules 
            (Student_ID, Course_ID, Course_Number, Course_Name, Section, Sunday, Monday, Tuesday, Wednesday, Thursday)
        VALUES 
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.executemany(insert_query, data_to_insert)
        mydb.commit()

        session.pop('df', None)
        cursor.close()
        mydb.close()
        
        message = "تم حفظ جدولك الدراسي بنجاح"
        category = "success"
        url = url_for('home')

        return render_template('imageTool.html', message=message, category=category, url=url)

    except pymysql.MySQLError as err:
        print(f"Database error: {err}")
        return jsonify({'error': 'Database error', 'message': str(err)}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({'error': 'Unexpected error', 'message': str(e)}), 500

@app.route('/delete_student_schedule', methods=['GET', 'POST'])
def deleteStudentSchedule():
    message = None
    category = None
        # url = None     
    if request.method == 'POST':
        student_id = session['academic_number']

        conn = db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM student_schedules WHERE Student_ID = %s", (student_id,))
        conn.commit()

        if cur.rowcount > 0:
            # message = 'لقد تم حذف جدولك الدراسي بنجاح!'
            # category = 'success'
            flash('لقد تم حذف جدولك الدراسي بنجاح!', 'success')
            messages = get_flashed_messages(with_categories=True)
        else:
            # message = 'جدولك الدراسي غير متوفر'
            # category = 'danger'
            flash('جدولك الدراسي غير متوفر', 'danger')
            messages = get_flashed_messages(with_categories=True) 
            
        cur.close()
        conn.close()

    return jsonify({"alert": messages})
# #
@app.route("/get_course_section", methods=['POST'])
def get_section():
    try:
        course_id = request.get_json().get('course_id')

        student_id = session['academic_number']

        conn = db_connection()
        cur = conn.cursor()
        query = "SELECT Course_ID, Course_Number, Section FROM student_schedules WHERE ID = %s AND Student_ID = %s"
        cur.execute(query, (course_id, student_id))
        course_info = cur.fetchone()
        cur.close()
        conn.close()


        no_conflict_sections = get_no_conflict_sections(student_id, course_info['Course_ID'], course_info['Course_Number'], course_info['Section'])

        data_output = {'currentSection': course_info['Section'], 'desiredSection': no_conflict_sections}

        if course_info:
            return jsonify(data_output)
        else:
            return jsonify({'error': 'Section not found'}), 404

    except pymysql.MySQLError as err:
        print(f"Database error: {err}")
        return jsonify({'error': 'Database error', 'message': str(err)}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({'error': 'Unexpected error', 'message': str(e)}), 500

@app.route('/submit_request', methods=['GET','POST'])
def submit():
    try:
        data = request.get_json().get('request_info') 
        student_id = session['academic_number']
        course_code_id = data.get('course_id')
        current_section = data.get('current_section')
        desired_section = data.get('desired_section')
        
        conn = db_connection()
        cur = conn.cursor()
        query = "SELECT * FROM student_schedules WHERE ID = %s AND Student_ID = %s"
        cur.execute(query, (course_code_id, student_id))
        course_info = cur.fetchone()


        course_id = course_info['Course_ID']
        course_number = course_info['Course_Number']
        course_name = course_info['Course_Name']

        
        get_advisor_email = "SELECT Academic_advisor_email, Email FROM users WHERE Academic_Number = %s"
        cur.execute(get_advisor_email,(student_id,))
        result = cur.fetchone()    
        advisor_email = result['Academic_advisor_email']

        isExists = check_request_exists(student_id,course_id,course_number)

        if isExists: 
            flash('لقد قدمت طلبًا لهذا المقرر مسبقًا!', 'danger')
            messages = get_flashed_messages(with_categories=True)
            return jsonify({'alert': messages})
        else:
            insert_query = """
                INSERT INTO requests_schedule 
                (Academic_Number, Course_ID, Course_Number, Course_Name, Current_Section, Desired_Section, Academic_advisor_email) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(insert_query, (student_id, course_id, course_number, course_name, current_section, desired_section, advisor_email))
            conn.commit()
            cur.close()
            conn.close()
    
    
        title = "رسالة تأكيد تقديم الطلب"
        subject = "تم استلام طلبك بنجاح"
        msg = f""" 
            <html>
            <body dir="rtl" style="font-family: Arial; text-align: right;">
                <p>عزيزنا الطالب/ عزيزتنا الطالبة،</p>
                <p>تم استلام طلبك الخاص بمقرر <strong> {course_name} </strong> بنجاح. سنقوم بمراجعته والرد عليك في أقرب وقت ممكن.</p>
                <p>يمكنك متابعة حالة الطلب من خلال لوحة التحكم الخاصة بك في “بدّيلي”</p>
                <p>مع تمنياتنا لك بالتوفيق, <br>فريق بدّيلي</p>
            </body>
            </html>        
        """
        email = [result['Email']]
        sendEmail(title, subject, msg, email) 

        filterRequests(course_id, course_number, session['major'], session['gender'])
        flash('لقد تم تقديم طلبك بنجاح!', 'success')
        messages = get_flashed_messages(with_categories=True)  

        return jsonify({'alert': messages}) , 200

    
    except pymysql.MySQLError as err:
        print(f"Database error sub: {err}")
        return jsonify({'error': 'Database error', 'message': str(err)}), 500
    except Exception as e:
        print(f"Unexpected error sub: {e}")
        return jsonify({'error': 'Unexpected error', 'message': str(e)}), 500

@app.route('/get_status')
def get_status():
    student_id = session['academic_number']
    data = get_status_from_db(student_id)
    return jsonify(data)

# 
@app.route("/requests_page", endpoint='requests_page')
def requestsPage():
    student_id = session['academic_number']
    data = get_student_requests(student_id)

    status_ar = {
        'pending': 'قيد الإجراء',
        'rejected': 'مرفوض',
        'approved': 'مكتمل',
        'pending_approval': 'بانتظار الموافقة'
    }

    for item in data:
        item['status_ar'] = status_ar.get(item['status'], item['status'])

    return render_template('requests.html', requests=data)

@app.route('/request_details', endpoint= 'request_details')
def requestsDetailsPage():
    student_id = session['academic_number']
    request_id = request.args.get('request_id')
    data = get_request_details(request_id, student_id)

    status_ar = {
        'pending': 'قيد الإجراء',
        'rejected': 'مرفوض',
        'approved': 'مكتمل',
        'pending_approval': 'بانتظار الموافقة'
    }
    

    for item in data:
        item['status'] = status_ar.get(item['status'], item['status'])

    return render_template('request_details.html', request_details = data)

@app.route('/cancel_request', methods=['POST'])
def cancelRequest():
    message = None
    category = None
    url = None 
    if request.method == 'POST':    
        request_id = request.form['request_id']  
        student_id = session['academic_number']  

        conn = db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Email FROM users
            WHERE Academic_Number = %s
        """, (student_id,))
        email = cursor.fetchone()  
        
        cursor.execute("""
            SELECT Course_Name FROM requests_schedule
            WHERE Request_ID = %s AND Academic_Number = %s
        """, (request_id, student_id))  
        course_name = cursor.fetchone()   

        cursor.execute("""
            DELETE FROM requests_schedule
            WHERE Request_ID = %s AND Academic_Number = %s
        """, (request_id, student_id))
        conn.commit()

        conn.close()
        cursor.close()
        
        title = "رسالة تأكيد إلغاء الطلب"
        subject = "تم إلغاء طلبك"
        msg = f""" 
            <html>
            <body dir="rtl" style="font-family: Arial; text-align: right;">
                <p>عزيزنا الطالب/ عزيزتنا الطالبة،</p>
                <p>تم إلغاء طلبك المتعلق بمقرر <strong> {course_name['Course_Name']} </strong>  بناءً على طلبك , يمكنك دائمًا إنشاء طلب جديد عند الحاجة من خلال النظام</p>
                <p>مع تمنياتنا لك بالتوفيق, <br>فريق بدّيلي</p>
            </body>
            </html>        
        """

        message = "تم إلغاء الطلب بنجاح"
        category = "success"
        url = url_for('requests_page')

        sendEmail(title, subject, msg, [email['Email']])
    
    # request_details.html
    
    return render_template('requests.html', message=message, category=category, url=url)



## Advisor
@app.route('/register_ac', methods=['GET', 'POST'], endpoint= 'register_ac')
def register_ac():

    message = None
    category = None
    url = None

    if request.method == 'POST':
        conn = db_connection()
        cur = conn.cursor()

        try:
            email = request.form['email'].strip()
            username = request.form['username'].strip()
            gender = request.form['gender'].strip()
            university_name = request.form['university_name'].strip()
            college = request.form['college'].strip()
            major = request.form['department'].strip()
            branch = request.form['branch'].strip()
            password = request.form['password']
            confirm_password = request.form['confirm_password']

            # Email validation
            if not EMAIL_PATTERN.match(email):
                message = "تنسيق البريد الإلكتروني غير صالح يجب ان ينتهي @taibahu.edu.sa"
                category = "danger"                

            # Password match validation
            if password != confirm_password:
                message = "كلمة المرور غير متطابقة!"
                category = "danger"                

            # Check if email already exists
            query_1 = "SELECT * FROM users WHERE email = %s"
            cur.execute(query_1, (email,))
            if cur.fetchone():
                message = "البريد الإلكتروني موجود بالفعل!"
                category = "danger" 

            # Hash password
            hashed_password = generate_password_hash(password)

            # Insert new user
            query_2 = """ 
                INSERT INTO users 
                (User_type, Email, Username, Gender, University, College, Major, Branch, Password) 
                VALUES ('Advisor', %s, %s, %s, %s, %s, %s, %s) 
            """
            cur.execute(query_2, (email, username, gender, university_name, college, major, branch, hashed_password))
            conn.commit()

            session['username'] = username
            session['email_ac'] = email
            session['gender_ac'] = gender
            session['department'] = major

            message = "تم إنشاء حسابك بنجاح!"
            category = "success" 
            url =  url_for('home_ac')

        finally:
            cur.close()
            conn.close()

    return render_template('register_ac.html', message=message, category=category, url=url)

@app.route('/home_ac', endpoint= 'home_ac')
def homePage_ac():
    return render_template('home_ac.html')

@app.route('/get_search_results_ac')
def search_ac():
    gender = session['gender_ac']
    department = session['department'] 
    request_id = request.args.get('request_id')
    data = get_search_result_ac(request_id, gender, department)
    return jsonify(data)

@app.route('/profile_ac', endpoint='profile_ac')
def profilePage_ac():
    info = get_user_advisor_info(session['email_ac'])

    value_translation = {
        'Taibahu':'طيبه',
        'Female': 'أنثى',
        'Male': 'ذكر',
        'Computer Science & Engineering': 'علوم وهندسة الحاسبات',
        'Computer Science': 'علوم الحاسب الآلي',
        'Information Systems': 'نظم المعلومات',
        'Computer Engineering':'هندسة الحاسب الآلي',
        'Cybersecurity':'الأمن السيبراني',
        'Artificial Intelligence and Data Science': 'الذكاء الاصطناعي وعلم البيانات'
    }

    for item in info:
        for key in item:
            if isinstance(item[key], str) and item[key] in value_translation:
                item[key] = value_translation[item[key]]
            
    return render_template('profile_ac.html', user_info = info)

@app.route("/update_profile_ac", methods=["POST"])
def update_profile_ac():

    conn = db_connection()
    cursor = conn.cursor()

    message = None
    category = None
    url = None      

    value_translation = {
        'طيبه' : 'Taibahu',
        'أنثى' : 'Female',
        'ذكر' : 'Male',
        'علوم وهندسة الحاسبات' : 'Computer Science & Engineering',
        'علوم الحاسب الآلي' : 'Computer Science',
        'نظم المعلومات' : 'Information Systems',
        'هندسة الحاسب الآلي' : 'Computer Engineering',
        'الأمن السيبراني' : 'Cybersecurity',
        'الذكاء الاصطناعي وعلم البيانات' : 'Artificial Intelligence and Data Science'
    }

    email = request.form['email'].strip()
    username = request.form['username'].strip()
    gender = value_translation.get(request.form['gender'].strip(), request.form['gender'].strip())
    university = value_translation.get(request.form['university'].strip(),request.form['university'].strip())
    college = value_translation.get(request.form['college'].strip(),request.form['college'].strip())
    major = value_translation.get(request.form['department'].strip(), request.form['department'].strip())  

    email_ac = session['email_ac']

    query = """
        UPDATE users SET Email = %s, Username = %s, Gender = %s, College = %s, 
        University = %s, Major = %s  WHERE Email = %s
    """ 

    cursor.execute(query ,(email,username,gender,college,university,major,email_ac))
    conn.commit()
    cursor.close()
    conn.close()

    message = "تم تحديث الملف الشخصي بنجاح!"
    category = "success"
    url = url_for('home_ac')

    return render_template("profile_ac.html", message=message, category=category, url=url)

@app.route('/get_status_ac')
def get_status_ac():
    department = session['department']
    gender = session['gender_ac']
    data = get_status_ac_from_db(department, gender)
    return jsonify(data)
# 
@app.route("/requests_ac", endpoint ='requests_ac')
def requestsPage_ac():
    data = get_accepted_requests(session['department'], session['gender_ac'])

    return render_template('requests_ac.html', requests = data)

@app.route('/request_details_ac', endpoint= 'request_details_ac')
def requestsDetailsPage_ac():
    try:
        request_id = request.args.get('request_id')
        data = get_request_details_accepted_requests(request_id)
    except Exception as e:
        print("Error in request_details_ac:", e)

    return render_template('request_details_ac.html' , request_details = data)

@app.route('/update_status', methods=['POST'])
def updateRequestStatus():
    status = request.form['status']
    note = request.form['note']
    request_id = request.form['request_id']
    
    message = None
    category = None
    url = None 

    conn = db_connection()
    cursor = conn.cursor()

    cursor.execute(""" SELECT course_name FROM accepted_requests WHERE match_id = %s""", (request_id,))
    course_name = cursor.fetchone()

    cursor.execute("""SELECT student1_id, student2_id, student3_id, student4_id, student5_id FROM accepted_requests WHERE match_id = %s""", (request_id,))

    student_ids_data = cursor.fetchone()  

    student_ids = [value for value in student_ids_data.values() if value is not None]

    if student_ids:
        placeholders = ', '.join(['%s'] * len(student_ids))
        query = f"SELECT Email FROM users WHERE Academic_Number IN ({placeholders})"
        cursor.execute(query, student_ids)

    emails_data = cursor.fetchall()
    student_emails = [row['Email'] for row in emails_data]

    cursor.execute("""
        SELECT course_id, course_number,
            student1_id, desired_section_1, 
            student2_id, desired_section_2, 
            student3_id, desired_section_3, 
            student4_id, desired_section_4, 
            student5_id, desired_section_5 
        FROM accepted_requests 
        WHERE match_id = %s
    """, (request_id,))

    row = cursor.fetchone()

    course_id = row[0]
    course_number = row[1]

    students = [
        (row[2], row[3]),  # student1
        (row[4], row[5]),  # student2
        (row[6], row[7]),  # student3
        (row[8], row[9]),  # student4
        (row[10], row[11])  # student5
    ]

    title = ""
    msg = ""
    subject = ""

    if(status == "approved"):
        title = "رسالة إشعار بقبول الطلب"
        subject = "تم قبول طلبك"
        msg = f"""
        <html>
        <body dir="rtl" style="font-family: Arial; text-align: right; color: #000;">
            <p>تهانينا!</p>

            <p>تمت الموافقة من لجنة الإرشاد الأكاديمي على طلبك لتبديل شعبة مقرر <strong>{course_name['course_name']}</strong><br>
            سيتم تحديث بيانات الجدول الدراسي وفق التغيير المعتمد</p>

            <p>للاطلاع على التفاصيل يمكنك زيارة حسابك في “بدّيلي”</p>

            <p>تحياتنا<br>
            فريق بدّيلي</p>
        </body>
        </html>
        """
        for student_id, desired_section in students:
            if student_id and desired_section:
                cursor.execute("""
                    SELECT Sunday, Monday, Tuesday, Wednesday, Thursday
                    FROM time_schedule 
                    WHERE Section = %s AND Course_ID = %s AND Course_Number = %s
                """, (desired_section, course_id, course_number))
                
                section_info = cursor.fetchone()
                if section_info:
                    sunday, monday, tuesday, wednesday, thursday = section_info

                    cursor.execute("""
                        UPDATE student_schedules
                        SET Section = %s,
                            Sunday = %s 
                            Monday = %s  
                            Tuesday = %s  
                            Wednesday = %s  
                            Thursday = %s 
                        WHERE Student_ID = %s AND Course_ID = %s AND Course_Number = %s
                    """, (desired_section, sunday, monday, tuesday, wednesday, thursday, student_id, course_id, course_number))
                    conn.commit()        
    else : 
        title = "رسالة إشعار برفض الطلب"
        subject = "نتأسف، لم يتم قبول طلبك"
        msg = f"""
            <html>
            <body dir="rtl" style="font-family: Arial; text-align: right; color: #000;">
                <p>عزيزنا الطالب / عزيزتنا الطالبة</p>

                <p>نعتذر، لم تتم الموافقة على طلبك بخصوص مقرر <strong>{course_name['course_name']}</strong> من قبل لجنة الإرشاد<br>
                يمكنك تقديم طلب جديد في أي وقت<br>
                أو مراجعة لجنة الإرشاد الأكاديمي لمزيد من التوضيح</p>

                <p>مع أطيب الأمنيات<br>
                فريق بدّيلي</p>
            </body>
            </html>
        """        


    cursor.execute("""
        UPDATE accepted_requests SET status = %s, note = %s WHERE match_id = %s
    """, (status, note, request_id))
    conn.commit()


    sendEmail(title, subject, msg, student_emails)

    conn.close()

    message = "تم تحديث الطلب بنجاح"
    category = "success"
    url = url_for('requests_ac')    

    return render_template("requests_ac.html", message=message, category=category, url=url)


## Admin
@app.route("/dashboard", endpoint = "dashboard")
def dashboard():
    conn = db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) As count FROM users WHERE User_Type = 'Student'")
    students_count = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) As count FROM users WHERE User_Type = 'Adivsor'")
    advisors_count = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) As count FROM requests_schedule")
    requests_count = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) As count FROM accepted_requests")
    accepted_requests_count = cursor.fetchone()

    query = """
        SELECT 
        DATE_FORMAT(created_at, '%M') AS month_name,
        COUNT(*) AS count
        FROM users
        GROUP BY month_name
        ORDER BY MIN(created_at);
    """
    cursor.execute(query)
    new_users = cursor.fetchall()

    labels_py = []
    data_py = []

    for row in new_users:
        labels_py.append(row['month_name'])
        data_py.append(row['count'])
    
    labels_json = json.dumps(labels_py)
    data_json = json.dumps(data_py) 

    query_2 = """
        SELECT Gender AS gender,
        COUNT(*) AS count
        FROM users
        GROUP BY gender;
    """
    cursor.execute(query_2)
    gender_out = cursor.fetchall()

    gender = []
    count = []

    for row in gender_out:
        gender.append(row['gender'])
        count.append(row['count']) 

    gender_json = json.dumps(gender)
    count_json = json.dumps(count) 

    query_3 = """
        SELECT status, COUNT(*) AS count 
        FROM (
            SELECT status FROM requests_schedule
            UNION ALL
            SELECT status FROM accepted_requests
        ) AS all_requests
        GROUP BY status;
    """
    cursor.execute(query_3)
    request_status = cursor.fetchall()

    pending_count = 0
    pending_approval_count = 0
    approved_count = 0
    rejected_count = 0

    for row in request_status:
        status = row[0] if isinstance(row, tuple) else row['status']
        count = row[1] if isinstance(row, tuple) else row['count']

        if status == 'pending':
            pending_count = count
        elif status == 'pending_approval':
            pending_approval_count = count
        elif status == 'approved':
            approved_count = count
        else:
            rejected_count = count
    

    cursor.close()
    conn.close()

    context = {
       "students_count": students_count['count'],
       "advisors_count": advisors_count['count'],
       "requests_count": requests_count['count'],
       "accepted_requests_count": accepted_requests_count['count'],
       "labels":labels_json,
       "data":data_json, 
       "g_labels": gender_json, 
       "g_data" : count_json, 
       "pending" : pending_count, 
       "pending_approval" : pending_approval_count, 
       "approved" : approved_count , 
       "rejected" : rejected_count
    }

    return render_template("dashbard.html", **context)

@app.route("/tables", endpoint = "tables")
def tables():
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    en_tables = [list(row.values())[0] for row in cursor.fetchall()]
    tables_name = {
        'accepted_requests': 'جدول الطلبات المتطابقة',
        'student_schedules': 'جدول جداول الطلاب',
        'requests_schedule': 'جدول الطلبات',
        'time_schedule': 'الجدول الزمني',
        'users': 'المستخدمين'
    }

    ar_tables_name = [tables_name[item] for item in en_tables]
    tables_name = list(zip(ar_tables_name, en_tables))
    cursor.close()
    conn.close()

    return render_template("tables.html", tebles= tables_name)

@app.route("/table/<table>")
def view_table(table):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute(f"DESCRIBE `{table}`")
    columns = [col["Field"] for col in cursor.fetchall()]

    cursor.execute(f"SELECT * FROM `{table}`")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("table.html", table=table, columns=columns, rows=rows)

# Add a row
@app.route("/table/<table>/add", methods=["POST"])
def add_row(table):
    conn = db_connection()
    cursor = conn.cursor()
    data = request.form.to_dict()
    columns = ", ".join(f"`{k}`" for k in data.keys())
    placeholders = ", ".join(["%s"] * len(data))
    values = list(data.values())

    sql = f"INSERT INTO `{table}` ({columns}) VALUES ({placeholders})"
    cursor.execute(sql, values)
    conn.commit()

    cursor.close()
    conn.close()

    return redirect(f"/table/{table}")

# Delete a row
@app.route("/table/<table>/delete/<int:row_id>", methods=["POST"])
def delete_row(table, row_id):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM `{table}` WHERE id = %s", (row_id,))
    conn.commit()

    cursor.close()
    conn.close()

    return "", 204

# Update a single cell
@app.route("/table/<table>/update/<int:row_id>", methods=["POST"])
def update_cell(table, row_id):
    conn = db_connection()
    cursor = conn.cursor()

    col_value_pairs = request.form.items() 
    set_clause = ", ".join([f"`{col}` = %s" for col, value in col_value_pairs])
    values = [value for col, value in col_value_pairs]

    cursor.execute(f"UPDATE `{table}` SET {set_clause} WHERE id = %s", (*values, row_id))
    conn.commit()

    cursor.close()
    conn.close()
    
    return "", 204  



if __name__ == '__main__':
    app.run()
