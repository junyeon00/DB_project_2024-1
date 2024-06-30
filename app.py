from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
import os

app = Flask(__name__)
app.secret_key = "1234"
app.config['UPLOAD_FOLDER'] = 'uploads/'

# 업로드 폴더 생성
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 역할에 따라 계정을 가져오는 함수
def get_accounts(role):
    db = pymysql.connect(host="localhost", user="root", password="junyeon123", db="term_project", charset="utf8")
    cursor = db.cursor()
    
    # 역할에 따라 다른 테이블에서 계정을 가져옴
    if role == "student":
        cursor.execute("SELECT id, password FROM stu_account")
    elif role == "staff":
        cursor.execute("SELECT id, password FROM pro_account")
    
    accs = cursor.fetchall()
    cursor.close()
    db.close()
    return {acc[0]: acc[1] for acc in accs}

# 로그인한 학생의 과제 목록을 가져오는 함수
def get_student_homework():
    db = pymysql.connect(host="localhost", user="root", password="junyeon123", db="term_project", charset="utf8")
    cursor = db.cursor()
    student_id = session.get("userID")  # 세션에서 로그인한 사용자의 아이디 가져오기
    cursor.execute("SELECT subject_name, project, duration FROM student_homework WHERE id = %s", (student_id,))
    homework_data = cursor.fetchall()
    cursor.close()
    db.close()
    return homework_data

# 로그인 페이지 라우트
@app.route("/login/", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    
    if request.method == "POST":
        role = request.form["role"]
        _id_ = request.form["loginID"]
        _password_ = request.form["loginPW"]
        
        accounts = get_accounts(role)

        # 학생 로그인 성공 시
        if _id_ in accounts and accounts[_id_] == _password_ and role == "student":
            session["userID"] = _id_
            return redirect(url_for("homework", user_id=_id_))
        
        # 교직원 로그인 성공 시
        if _id_ in accounts and accounts[_id_] == _password_ and role == "staff":
            session["userID"] = _id_
            return redirect(url_for("edit_homework", user_id=_id_))
        
        flash("로그인에 실패하였습니다. 다시 시도해주세요")
        return redirect(url_for("login"))

# 로그아웃 라우트
@app.route("/logout/")
def logout():
    session.pop("userID", None)
    return redirect(url_for("login"))

# 학생 과제 페이지 라우트
@app.route("/homework/<user_id>")
def homework(user_id):
    if "userID" in session and session["userID"] == user_id:
        student_homework = get_student_homework()
        return render_template("homework.html", student_homework=student_homework)
    else:
        flash("로그인이 필요합니다.")
        return redirect(url_for("login"))

# 교직원 과제 수정 페이지 라우트
@app.route('/edit_homework/', methods=['GET', 'POST'])
def edit_homework():
    user_id = request.args.get('user_id')
    
    if not user_id:
        return "User ID is required", 400

    if request.method == 'POST':
        selected_subject_name = request.form['subject_name']
        project = request.form['project']
        duration = request.form['duration']

        db = pymysql.connect(host="localhost", user="root", password="junyeon123", db="term_project", charset="utf8")
        cursor = db.cursor()

        # subject_name으로 subject_id 가져오기
        cursor.execute("SELECT subject_id FROM subject_list WHERE subject_name = %s", (selected_subject_name,))
        subject = cursor.fetchone()
    
        if subject:
            subject_id = subject[0]

            # homework 테이블 업데이트
            cursor.execute("""
            INSERT INTO homework (project, duration, homework_subject_id)
            VALUES (%s, %s, %s)
            """, (project, duration, subject_id))

            db.commit()

        # student_homework 뷰 업데이트
        cursor.execute("""CREATE OR REPLACE VIEW student_homework AS 
                              SELECT sa.id, sl.subject_name, hw.project, hw.duration
                            FROM
	                            stu_account sa
                            INNER JOIN 
	                            student_subjects ss ON sa.id = ss.student_id
                            INNER JOIN 
	                            subject_list sl ON ss.student_subject_id = sl.subject_id
                            INNER JOIN
	                            homework hw ON sl.subject_name = hw.homework_subject_name; """)  # 뷰의 쿼리를 다시 실행하여 업데이트된 데이터를 반영

        cursor.close()
        db.close()

        return redirect(url_for('edit_homework', user_id=user_id))

    db = pymysql.connect(host="localhost", user="root", password="junyeon123", db="term_project", charset="utf8")
    cursor = db.cursor()
    
    # 사용자 ID에 해당하는 과목명 가져오기
    cursor.execute("""
        SELECT sl.subject_name
        FROM pro_account pa
        INNER JOIN professor_subjects ps ON pa.id = ps.professor_id
        INNER JOIN subject_list sl ON ps.professor_subject_id = sl.subject_id
        WHERE pa.id = %s
        """, (user_id,))
    subjects = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('edit_homework.html', subjects=subjects, user_id=user_id)

if __name__ == "__main__":
    app.run(debug=True)
