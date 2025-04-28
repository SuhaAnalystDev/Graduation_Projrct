import os
import pytest
import io
from flask import session
import pandas as pd
import google.generativeai as genai
from app import app, db_connection

@pytest.fixture
def client():
    os.environ['FLASK_ENV'] = 'testing'  # تعيين البيئة إلى الاختبار
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client

def insert_test_users():
    conn = db_connection()
    cursor = conn.cursor()
    delete_test_switch_requests()
    delete_test_matched_requests()
    delete_test_users()

    cursor.execute("""
        INSERT INTO users (ID, User_type, Academic_Number, Email, Username,
        Gender, College, University, Major, Academic_advisor_email, Password, Academic_Number_Unique)
        VALUES (
            1, 'student', '12345678', 'badeely.system@gmail.com', 'TestUser',
            'male', 'Engineering', 'Test University', 'Computer Science',
            'advisor@example.com', 'scrypt:32768:8:1$3j2bJgJstQeC2bGw$b9814bf69732f2bd7e1cfb87aab4c73e3f47646976b02e942d21e907cfb716a90592e3fab6cd5c698967a1b5ea4d2aafc623bab6354367ee0cb66a32ea12e5bb','12345678'
        ), (
            2, 'student', '87654321', 'badeely.system@gmail.com', 'TestUser',
            'male', 'Engineering', 'Test University', 'Computer Science',
            'advisor@example.com', 'scrypt:32768:8:1$3j2bJgJstQeC2bGw$b9814bf69732f2bd7e1cfb87aab4c73e3f47646976b02e942d21e907cfb716a90592e3fab6cd5c698967a1b5ea4d2aafc623bab6354367ee0cb66a32ea12e5bb','87654321'
        )
    """)   
    conn.commit()
    cursor.close()
    conn.close()

def insert_test_users_ac():
    conn = db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO users (ID, User_type, Email, Username,
        Gender, College, University, Major, Password)
        VALUES (
            3, 'Advisor', 'test@example.com', 'TestUser',
            'male', 'Engineering', 'Test University', 'Computer Science', 'hashedpassword'
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()    

def insert_test_matched_requests():
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("""
                    INSERT INTO matched_requests (match_id, student1_id, current_section_1, desired_section_1, academic_advisor_email_1, student2_id, current_section_2, desired_section_2, academic_advisor_email_2,
                    student3_id, current_section_3, desired_section_3, academic_advisor_email_3, student4_id, current_section_4, desired_section_4, academic_advisor_email_4, student5_id, current_section_5,
                    desired_section_5, academic_advisor_email_5, course_id, course_number, course_name, advisory_committee_name, advisory_committee_email, gender, department, status, note) VALUES 
                    (11112222, '12345678', 'F2', 'F7', 'advisor@example.com', '87654321', 'F7', 'F2', 'advisor@example.com', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'CS', '424', 
                    'مقدمة في الحوسبة المتوازية', 'فاطمة الشمري', 'advisor@example.com', 'Female', 'Computer Science', 'pending_approval', '-')
    """)
    conn.commit()
    cursor.close()
    conn.close()

def insert_test_switch_requests():
    conn = db_connection()
    cursor = conn.cursor()
    delete_test_switch_requests()
    cursor.execute("""
            INSERT INTO switch_requests (Request_ID, Academic_Number, Course_ID, Course_Number, Course_Name, Current_Section, Desired_Section, Academic_advisor_email, Status, Note) 
            VALUES (1, '12345678', 'CS', '424', 'مقدمة في الحوسبة المتوازية', 'F1', 'F3', 'advisor@example.com', 'pending', '-')
    """)
    conn.commit()
    cursor.close()
    conn.close()

def insert_test_student_schedules():
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM student_schedules")
    conn.commit()
    cursor.execute("""INSERT INTO student_schedules (ID, Student_ID, Course_ID, Course_Number, Course_Name, Section, Sunday, Monday, Tuesday, Wednesday, Thursday) VALUES 
    (1, '12345678', 'CS', '424', 'مقدمة في الحوسبة المتوازية', 'F1', '-', '-', '08:30-09:45', '08:30-09:45', '08:30-10:10'), 
    (2, '12345678', 'CS', '492', 'مشروع التخرج (2)', 'F43', '20:00-21:30', '-', '-', '-', '20:00-21:30'), 
    (3, '12345678', 'MATH', '204', '(2) تفاضل وتكامل', 'F21', '13:00-14:15', '-', '-', '11:20-12:35', '-'),
    (4, '87654321', 'CS', '424', 'مقدمة في الحوسبة المتوازية', 'F3', '09:55-11:10', '09:55-11:10', '-', '08:30-10:10', '-'), 
    (5, '87654321', 'CS', '486', 'إدراة مشاريع البرمجيات', 'F2', '14:30-15:45', '-', '14:30-15:45', '-', '-'), 
    (6, '87654321', 'CS', '492', 'مشروع التخرج (2)', 'F43', '20:00-21:30', '-', '-', '-', '20:00-21:30'), 
    (7, '87654321', 'GS', '136', 'مقدمة في البيئة والتنمية المستدامة', 'F4', '-', '-', '-', '17:40-19:20', '-')
    """)
    conn.commit()
    cursor.close()
    conn.close()

def insert_test_time_schedule():
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM time_schedule")
    conn.commit()
    cursor.execute("""
        INSERT INTO time_schedule (ID, Branch, Course_ID, Course_Number, Course_Name, Section, Sunday, Monday, Tuesday, Wednesday, Thursday, Available, Registered) VALUES
        (1, 'Madinah', 'CS', '424', 'مقدمة في الحوسبة المتوازية', 'F1', '-', '-', '08:30-09:45', '08:30-09:45', '08:30-10:10', 30, 32),
        (2, 'Madinah', 'CS', '424', 'مقدمة في الحوسبة المتوازية', 'F2', '-', '-', '09:55-11:10', '09:55-11:10', '10:20-12:00', 37, 37),
        (3, 'Madinah', 'CS', '424', 'مقدمة في الحوسبة المتوازية', 'F3', '09:55-11:10', '09:55-11:10', '-', '08:30-10:10', '-', 30, 26),
        (4, 'Madinah', 'CS', '424', 'مقدمة في الحوسبة المتوازية', 'F4', '11:20-12:35', '11:20-12:35', '-', '10:20-12:00', '-', 35, 35),
        (5, 'Madinah', 'CS', '424', 'مقدمة في الحوسبة المتوازية', 'F5', '09:55-11:10', '09:55-11:10', '-', '10:20-12:00', '-', 32, 25),
        (6, 'Madinah', 'CS', '424', 'مقدمة في الحوسبة المتوازية', 'F6', '-', '09:55-11:10', '-', '09:55-11:10', '13:00-14:40', 37, 36),
        (7, 'Madinah', 'CS', '424', 'مقدمة في الحوسبة المتوازية', 'F7', '-', '-', '08:30-10:10', '08:30-09:45', '09:55-11:20', 34, 33),
        (8, 'Madinah', 'CS', '424', 'مقدمة في الحوسبة المتوازية', 'F8', '08:30-10:10', '08:30-09:45', '-', '-', '08:30-09:45', 31, 28),
        (9, 'Madinah', 'CS', '435', 'علم التشفير', 'F1', '13:00-14:15', '-', '13:00-14:15', '-', '-', 47, 45),
        (10, 'Madinah', 'CS', '435', 'علم التشفير', 'F3', '-', '13:00-14:15', '-', '13:00-14:15', '-', 43, 40),
        (11, 'Madinah', 'CS', '492', 'مشروع التخرج (2)', 'F43', '20:00-21:30', '-', '-', '-', '20:00-21:30', 6, 6),
        (12, 'Madinah', 'STAT', '301', 'الإحتمالات ولإحصاء للمهندسين', 'F3', '09:50- 11:30', '-', '13:00-14:40', '-', '-', 40, 40),
        (13, 'Madinah', 'CS', '403', 'بناء المترجمات', 'F1', '16:00-17:15', '-', '16:00-17:15', '-', '-', 47, 47),
        (14, 'Madinah', 'CS', '486', 'إدراة مشاريع البرمجيات', 'F2', '14:30-15:45', '-', '14:30-15:45', '-', '-', 45, 45),
        (15, 'Madinah', 'CS', '486', 'إدارة مشاريع البرمجيات', 'F3', '08:30-09:40', '08:30-09:40', '-', '-', '-', 48, 47),
        (16, 'Madinah', 'CS', '486', 'إدارة مشاريع البرمجيات', 'F4', '09:55-11:10', '09:55-11:10', '-', '-', '-', 48, 48),
        (17, 'Madinah', 'GS', '136', 'مقدمة في البيئة والتنمية المستدامة', 'F4', '-', '-', '-', '17:40-19:20', '-', 100, 100),
        (18, 'Madinah', 'MATH', '204', '(2) تفاضل وتكامل', 'F21', '13:00-14:15', '-', '-', '11:20-12:35', '-', 42, 41),
        (19, 'Madinah', 'COE', '332', 'شبكات الحاسب', 'F4', '-', '08:00-09:15', '-', '08:00-09:15', '08:00-09:40', 0, 0),
        (20, 'Madinah', 'CS', '405', 'تحليل الخوارزميات', 'F4', '08:30-09:45', '-', '08:30-09:45', '-', '-', 0, 0),
        (21, 'Madinah', 'CS', '492', '(2) مشروع التخرج', 'F37', '-', '-', '-', '20:00-21:30', '20:00-21:30', 0, 0),
        (22, 'Madinah', 'GS', '103', 'دراسات اسلامية: حقوق الإنسان في الإسلام', 'F27', '15:50:17:30', '-', '-', '-', '-', 0, 0);


    """)
    conn.commit()
    cursor.close()
    conn.close()

def insert_test_majors():
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM majors WHERE ID = 1")
    cursor.execute("INSERT INTO majors (ID, Name, CollegeID) VALUES (1, 'Computer Science', 1)")
    conn.commit()
    cursor.close()
    conn.close()

def delete_test_users():
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users")
    conn.commit()
    cursor.execute("ALTER TABLE users AUTO_INCREMENT = 1")
    conn.commit()
    cursor.close()
    conn.close()

def delete_test_matched_requests():
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM matched_requests")
    conn.commit()
    cursor.close()
    conn.close()

def delete_test_switch_requests():
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM switch_requests")
    conn.commit()
    cursor.close()
    conn.close()

def delete_test_registrations():
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM registrations WHERE ID = 1")
    conn.commit()
    cursor.close()
    conn.close()

def delete_test_colleges():
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM colleges WHERE ID = 1")
    conn.commit()
    cursor.close()
    conn.close()



# #########################################################################################################################  

# def test_index_page_route(client):
#     response = client.get('/')

#     assert response.status_code == 200
#     assert '<html' in response.data.decode()  

# def test_register_page_route(client):
#     response = client.get('/register_page')

#     assert response.status_code == 200
#     assert '<html' in response.data.decode()

# def test_login_page_route(client):
#     response = client.get('/login_page')

#     assert response.status_code == 200
#     assert '<html' in response.data.decode()    

# def test_forgot_password_page_route(client):
#     response = client.get('/forgot_password_page')

#     assert response.status_code == 200
#     assert '<html' in response.data.decode()

# def test_reset_password_page_route(client):
#     response = client.get('/reset_password_page')

#     assert response.status_code == 200
#     assert '<html' in response.data.decode()    

# def test_home_page_route(client):
#     response = client.get('/home')

#     assert response.status_code == 200
#     assert '<html' in response.data.decode()

# def test_home_ac_page_route(client):
#     response = client.get('/home_ac')

#     assert response.status_code == 200
#     assert '<html' in response.data.decode()

# def test_register_route(client):
#     delete_test_users()
#     response = client.post("/register", data={
#         "academic_number": "4325999",
#         "email": "updated@example.com",
#         "username": "Updated Name",
#         "gender": "Female",
#         "university_name": "Taibahu",
#         "college": "Science",
#         "major": "Computer Science",
#         "academic_advisor_email": "newadvisor@example.com",
#         "password": "123",
#         "confirm_password":"123",
#         "Academic_Number_Unique": "4325999"
#     })

#     assert response.status_code == 200

#     conn = db_connection()
#     cursor = conn.cursor()

#     cursor.execute("""
#         SELECT Email, Username, Gender, College, University, Major, Academic_advisor_email FROM users""")

#     user = cursor.fetchone()
#     print("Fetched user:", user)

#     assert user == (
#         "updated@example.com",
#         "Updated Name",
#         "Female",
#         "Science",
#         "Taibahu",
#         "Computer Science",
#         "newadvisor@example.com"
#     )

#     cursor.close()
#     conn.close()

# def test_register_ac_route(client):
#     delete_test_users()
#     response = client.post("/register_ac", data={
#         "email": "updated@example.com",
#         "username": "Updated Name",
#         "gender": "Female",
#         "university_name": "Taibahu",
#         "college": "Science",
#         "department": "Computer Science",
#         "password": "123",
#         "confirm_password":"123"
#     })

#     assert response.status_code == 200

#     conn = db_connection()
#     cursor = conn.cursor()

#     cursor.execute("""
#         SELECT Email, Username, Gender, College, University, Major, Academic_advisor_email FROM users""")

#     user = cursor.fetchone()
#     print("Fetched user:", user)

#     assert user == (
#         "updated@example.com",
#         "Updated Name",
#         "Female",
#         "Science",
#         "Taibahu",
#         "Computer Science"
#     )

#     cursor.close()
#     conn.close()

# def test_login_route(client):
#     insert_test_users() 

#     response = client.post("/login", data={
#         "email": "test@example.com",
#         "password": "232",
#     })

#     assert response.status_code == 200
#     assert "تم تسجيل الدخول بنجاح!" in response.data.decode('utf-8')
#     assert 'window.location.href = "/home";' in response.data.decode('utf-8')

# def test_checkEmail_route(client):
#     insert_test_users() 

#     response = client.post("/check_email", data={
#         "email": "test@example.com"
#     })

#     assert response.status_code == 200
#     assert 'window.location.href = "/reset_password_page";' in response.data.decode('utf-8')

# def test_resetPassword_route(client):
#     insert_test_users() 
#     with client.session_transaction() as session:
#         session['resetPassword_email'] = "test@example.com" 
#     response = client.post("/reset_password", data={
#         "password": "123",
#         "confirm_password": "123"
#     })

#     assert response.status_code == 200
#     assert "تم إعادة إنشاء كلمة المرور بنجاح" in response.data.decode('utf-8')
#     assert 'window.location.href = "/login";' in response.data.decode('utf-8')

# def test_get_name_route(client):
#     with client.session_transaction() as session:
#         session['username'] = 'TestUser'

#     response = client.get('/get_username')

#     assert response.status_code == 200
#     assert response.get_json() == {'username': 'TestUser'}

# def test_profile_route(client):
#     with client.session_transaction() as session:
#         session['academic_number'] = "12345678"   

#     insert_test_users()

#     response = client.get('/profile')

#     assert response.status_code == 200
#     assert b'TestUser' in response.data
#     response_text = response.data.decode('utf-8')
#     assert 'علوم الحاسب الآلي' in response_text

# def test_update_profile_route(client):
#     insert_test_users() 

#     with client.session_transaction() as session:
#         session['academic_number'] = "12345678"

#     response = client.post("/update_profile", data={
#         "academic_number": "4325999",
#         "email": "updated@example.com",
#         "username": "Updated Name",
#         "gender": "أنثى",
#         "college": "Science",
#         "university": "طيبه",
#         "major": "الأمن السيبراني",
#         "academic_advisor_email": "newadvisor@example.com",
#         "Academic_Number_Unique": "4325999"
#     })

#     assert response.status_code == 200

#     conn = db_connection()
#     cursor = conn.cursor()

#     cursor.execute(""" SELECT Email, Username, Gender, College, University, Major, Academic_advisor_email FROM users """)

#     user = cursor.fetchone()
#     print("Fetched user:", user)

#     assert user == (
#         "updated@example.com",
#         "Updated Name",
#         "Female",
#         "Science",
#         "Taibahu",
#         "Cybersecurity",
#         "newadvisor@example.com"
#     )

#     cursor.close()
#     conn.close()

# def test_profile_ac_route(client):
#     with client.session_transaction() as session:    
#         session['email_ac'] = "test@example.com"

#     insert_test_users_ac()
#     response = client.get('/profile_ac')

#     assert response.status_code == 200
#     assert b'TestUser' in response.data
#     response_text = response.data.decode('utf-8')
#     assert 'علوم الحاسب الآلي' in response_text

# def test_update_profile_ac_route(client):
#     insert_test_users_ac()

#     with client.session_transaction() as session:
#         session['email_ac'] = "test@example.com"

#     response = client.post("/update_profile_ac", data={
#         "email": "updated@example.com",
#         "username": "Updated Name",
#         "gender": "أنثى",
#         "university": "طيبه",
#         "college": "Science",
#         "department": "الأمن السيبراني"
#     })

#     assert response.status_code == 200

#     conn = db_connection()
#     cursor = conn.cursor()

#     cursor.execute(""" SELECT Email, Username, Gender, College, University, Major FROM users""")

#     user = cursor.fetchone()
#     print("Fetched user:", user)

#     assert user == (
#         "updated@example.com",
#         "Updated Name",
#         "Female",
#         "Science",
#         "Taibahu",
#         "Cybersecurity"
#     )

#     cursor.close()
#     conn.close()

# def test_get_search_results_route(client):
#     insert_test_users()
#     insert_test_matched_requests()

#     with client.session_transaction() as session:
#         session['academic_number'] = "12345678"

#     response = client.get('/get_search_results?request_id=11112222')

#     assert response.status_code == 200
#     assert response.get_json() == [{'id': 11112222}]

# def test_get_search_results_ac_route(client):
#     insert_test_users()
#     insert_test_users_ac()
#     insert_test_matched_requests()

#     with client.session_transaction() as session:
#         session['gender_ac'] = "Female"
#         session['department'] = "Computer Science"

#     response = client.get('/get_search_results_ac?request_id=11112222')

#     assert response.status_code == 200
#     assert response.get_json() == [{'id': 11112222}]    

# def test_get_course_section_route(client):
#     insert_test_users()
#     insert_test_student_schedules()
#     insert_test_time_schedule()

#     with client.session_transaction() as session:
#         session['academic_number'] = "12345678"

#     jsonBody = {'course_id': '1'}
#     response = client.post('/get_course_section', json=jsonBody)

#     assert response.status_code == 200
#     assert response.get_json() == {'currentSection': 'F1', 'desiredSection' :  ['F2', 'F3', 'F6', 'F7', 'F8']}

# def test_get_submit_request_route(client):
#     insert_test_users()
#     insert_test_student_schedules()
#     insert_test_time_schedule()

#     with client.session_transaction() as session:
#         session['academic_number'] = "12345678"
#         session['major']= "Computer Science"
#         session['gender'] = "Male"


#     jsonBody = {
#         'request_info': {
#             'course_id': '1',
#             'current_section': 'F1',
#             'desired_section': 'F3'
#         }
#     }
#     response = client.post('/submit_request', json=jsonBody)

#     assert response.status_code == 200
#     assert response.get_json() == {'alert': [['success', 'لقد تم تقديم طلبك بنجاح!']]}

# def test_get_status_route(client):
#     insert_test_users()
#     insert_test_switch_requests()
#     insert_test_matched_requests()

#     with client.session_transaction() as session:
#         session['academic_number'] = "12345678"

#     response = client.get('/get_status')
#     assert response.status_code == 200
#     assert response.get_json() == {'pending': 1, 'pending_approval': 1, 'total': 2}

# def test_switch_sectinon_request_page_route(client):
#     insert_test_users()
#     insert_test_student_schedules()
#     insert_test_time_schedule()

#     with client.session_transaction() as session:
#         session['academic_number'] = "12345678"   

#     response = client.get('/switch_sectinon_request_page')

#     assert response.status_code == 200
#     assert 'CS424 - مقدمة في الحوسبة المتوازية' in response.data.decode()

# def test_requests_ac_route(client):
#     insert_test_users_ac()
#     insert_test_matched_requests()

#     with client.session_transaction() as session:
#         session['department'] = "Computer Science"
#         session['gender_ac'] = "Female"

#     response = client.get('/requests_ac')
#     assert response.status_code == 200
#     assert b"11112222" in response.data

# def test_request_details_ac_route(client):
#     insert_test_users()
#     insert_test_users_ac()
#     insert_test_matched_requests()

#     with client.session_transaction() as session:
#         session['department'] = "Computer Science"
#         session['gender_ac'] = "male"

#     response = client.get('/request_details_ac?request_id=11112222')
#     assert response.status_code == 200
#     assert b"11112222" in response.data

def test_update_status_route(client):
    insert_test_users()
    insert_test_users_ac()
    insert_test_matched_requests()

    data = {
        'status': 'approved',
        'note': 'accepted',
        'request_id': '11112222'
    }

    response = client.post('/update_status', data=data)

    assert response.status_code == 200
    assert "تم تحديث الطلب بنجاح" in response.data.decode('utf-8')

import io
import pytest

# def test_upload_and_save_route(client):
#     with client.session_transaction() as session:
#         session['academic_number'] = "12345678"  
         
#     with open('static/images/test_image.jpg', 'rb') as f:
#         data = {
#             'image': (f, 'test_image.jpg')
#         }
        
#         response = client.post('/upload', data=data, content_type='multipart/form-data')
        
#         assert response.status_code == 200
#         assert b'<table' in response.data

#         response = client.post('/save')
#         assert response.status_code == 200
#         assert "تم حفظ جدولك الدراسي بنجاح" in response.data.decode('utf-8')



if __name__ == "__main__":
    pytest.main()