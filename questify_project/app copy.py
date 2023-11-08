import pymysql
import hashlib
import uuid
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g





app = Flask(__name__)

# Allow flask to encrypt the session cookie.
app.secret_key = "any-random-string-reshrdjtfkygluvchfjkhlbh"

def create_connection():
    return pymysql.connect(
        host="127.0.0.1",
        user="root",
        # host="localhost",
        # user="root",
        password="ANKLE",
        db="flask_practice",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
        )


def can_access():
    if "logged_in" in session:
        matching_id = session["id"] == int(request.args["id"])
        is_admin = session["role"] == "admin"
        return matching_id or is_admin
    else:
        return False

def encrypt(password):
    return hashlib.sha256(password.encode()).hexdigest()

def email_exists(email):
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users WHERE email = %s"
            values = (email)
            cursor.execute(sql, values)
            result = cursor.fetchone()
    return result is not None

# This runs before every page request.
# If it returns something, the request will be prevented.
@app.before_request
def load_classes_for_layout():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT id, class_name FROM classes"
            cursor.execute(sql)
            g.classes = cursor.fetchall()

@app.route("/")
def home():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users"
            cursor.execute(sql)
            users = cursor.fetchall()

            # Fetching the classes
            sql = "SELECT id, class_name FROM classes"
            cursor.execute(sql)
            classes = cursor.fetchall()

    return render_template("home.html", result=users, classes=classes)  # passing the classes to the template



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """SELECT * FROM users
                         WHERE email = %s AND password = %s"""
                values = (
                    request.form["email"],
                    encrypt(request.form["password"])
                )
                cursor.execute(sql, values)
                result = cursor.fetchone()

        if result:
            session["logged_in"] = True
            session["id"] = result["id"]
            session["first_name"] = result["first_name"]
            session["role"] = result["role"]
            
            # Set the user_id session variable
            session["user_id"] = result["id"]
            
            return redirect("/")
        else:
            flash("Wrong username or password!")
            return redirect("/login")
    else:
        # Fetching the classes for GET method
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT id, class_name FROM classes"
                cursor.execute(sql)
                classes = cursor.fetchall()
        return render_template("login.html", classes=classes)



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        if email_exists(request.form["email"]):
            flash("That email already exists.")
            return redirect("/signup")
        with create_connection() as connection:
            with connection.cursor() as cursor:

                image = request.files["image"]
                if image:
                    # Choose a random filename to prevent clashes
                    ext = os.path.splitext(image.filename)[1]
                    image_path = "static/images/" + str(uuid.uuid4())[:8] + ext
                    image.save(image_path)
                else:
                    image_path = None

                # Any input from the user should be replaced by '%s',
                # so that their input isn't accidentally treated as bits of SQL.
                sql = """INSERT INTO users
                    (first_name, last_name, email, password, birthday, image)
                    VALUES (%s, %s, %s, %s, %s, %s)"""
                values = (
                    request.form["first_name"],
                    request.form["last_name"],
                    request.form["email"],
                    encrypt(request.form["password"]),
                    request.form["birthday"],
                    image_path
                )
                cursor.execute(sql, values)
                user_id = cursor.lastrowid # Get the newly inserted user ID

                # Insert selected classes
                selected_classes = request.form.getlist("classes")
                for selected_class in selected_classes:
                    sql = "INSERT INTO user_class (user_id, class_id) VALUES (%s, %s)"
                    values = (user_id, selected_class)
                    cursor.execute(sql, values)

                connection.commit() # Save to the database

                # Select the new user details and store them in session
                sql = "SELECT * FROM users WHERE email = %s"
                values = (request.form["email"],)
                cursor.execute(sql, values)
                result = cursor.fetchone()
                session["logged_in"] = True
                session["id"] = result["id"]
                session["first_name"] = result["first_name"]
                session["role"] = result["role"]

        return redirect("/questify")
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT id, class_name FROM classes"
                cursor.execute(sql)
                classes = cursor.fetchall()
        return render_template('signup.html', classes=classes)



# /view?id=1
@app.route("/view")
def view():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users WHERE id = %s"
            values = (request.args["id"])
            cursor.execute(sql, values)
            result = cursor.fetchone()
    return render_template("view.html", result=result)

@app.route("/save-image", methods=["POST"])
def save_image():
    image = request.files["image"]
    if image:
        # Choose a random filename to prevent clashes
        ext = os.path.splitext(image.filename)[1]
        image_path = "static/images/" + str(uuid.uuid4())[:8] + ext
        image.save(image_path)
        image_path = "/" + image_path
    else:
        image_path = None
    return { "default": image_path }


# /post?id=1
@app.route("/post")
def post():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """SELECT * FROM posts
                    LEFT JOIN users ON posts.user_id = users.id
                    WHERE posts.id = %s"""
            values = (request.args["id"])
            cursor.execute(sql, values)
            result = cursor.fetchone()
    return render_template("post_view.html", result=result)

from werkzeug.utils import secure_filename

from flask import redirect

@app.route("/post/add", methods=["GET", "POST"])
def add_post():
    if request.method == "POST":
        user_id = session["id"]
        content = request.form["content"]
        class_id = request.form["class_id"]
        if not class_id:
            return "Class ID is missing", 400  # Return an error response
        image = request.files.get("image")
        image_path = None
        if image and image.filename and '.' in image.filename and image.filename.rsplit('.', 1)[1].lower() in ['png', 'jpg', 'jpeg']:
            filename = secure_filename(image.filename)
            image_path = os.path.join('static/uploads/', filename)
            image.save(image_path)
        
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "INSERT INTO posts (content, user_id, image, class_id) VALUES (%s, %s, %s, %s)"
                values = (content, user_id, image_path, class_id)
                cursor.execute(sql, values)
                connection.commit()
        
        return redirect("/q_post")
    else:
        # Fetching the classes
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT id, class_name FROM classes"
                cursor.execute(sql)
                classes = cursor.fetchall()
        return render_template("post_add.html", classes=classes)

@app.route("/q_post")
def q_post():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """
                  SELECT posts.id, posts.content, posts.image, 
                         CONCAT(users.first_name, ' ', users.last_name) AS user_name,
                         classes.class_name
                  FROM posts
                  JOIN users ON posts.user_id = users.id
                  JOIN classes ON posts.class_id = classes.id
                  """
            cursor.execute(sql)
            posts = cursor.fetchall()
    return render_template("questify_post.html", posts=posts)

@app.route('/class_page/<class_name>')
def class_page(class_name):
    # You can fetch information related to the class here
    return render_template('class_page.html', class_name=class_name)

@app.route("/questify")
def questify():
    if 'id' not in session:
        flash('Please log in to access this page.')
        return redirect(url_for('login'))

    user_id = session['id']
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """
                SELECT classes.id, classes.class_name 
                FROM classes 
                JOIN user_class ON classes.id = user_class.class_id
                WHERE user_class.user_id = %s
            """
            cursor.execute(sql, (user_id,))
            user_classes = cursor.fetchall()

    return render_template('questify_home.html', classes=user_classes)



@app.route('/add_todo', methods=['POST'])
def add_todo():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    task_description = request.json.get('task_description')
    due_date = request.json.get('due_date')
    is_complete = request.json.get('is_complete', False)

    # Input validation
    if not task_description:
        return jsonify({'error': 'Task description is required'}), 400

    try:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = """INSERT INTO todo_list (user_id, task_description, due_date, is_complete)
                         VALUES (%s, %s, %s, %s)"""
                cursor.execute(sql, (user_id, task_description, due_date, is_complete))
                connection.commit()

        return jsonify({'success': True}), 200

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': 'An error occurred while adding the todo'}), 500


@app.route('/list_todos', methods=['GET'])
def list_todos():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    try:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM todo_list WHERE user_id = %s"
                cursor.execute(sql, (user_id,))
                todos = cursor.fetchall()

        return jsonify({'todos': todos}), 200

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': 'An error occurred while listing the todos'}), 500


@app.route('/update_todo/<int:todo_id>', methods=['POST'])
def update_todo(todo_id):
    is_complete = request.json.get('is_complete')

    try:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "UPDATE todo_list SET is_complete = %s WHERE id = %s"
                cursor.execute(sql, (is_complete, todo_id))
                connection.commit()

        return jsonify({'success': True}), 200

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': 'An error occurred while updating the todo'}), 500


@app.route('/delete_todo/<int:todo_id>', methods=['POST'])
def delete_todo(todo_id):
    try:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "DELETE FROM todo_list WHERE id = %s"
                cursor.execute(sql, (todo_id,))
                connection.commit()

        return jsonify({'success': True}), 200

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': 'An error occurred while deleting the todo'}), 500





@app.route("/list_classes", methods=["GET"])
def list_classes():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT id, class_name FROM classes"
            cursor.execute(sql)
            classes = cursor.fetchall()
    return jsonify({'classes': classes}), 200




@app.route('/class_posts/<int:class_id>', methods=['GET', 'POST'], endpoint='class_posts')
def class_posts_route(class_id):
    print(f"Debug: Session: {session}")  # Debug line
    print(f"Debug: class_id: {class_id}")  # Debug line
    
    if 'current_class_id' in session:
        print("current_class_id exists in session and its value is:", session['current_class_id'])
    else:
        print("current_class_id does not exist in session")
    
    # ... rest of your code

    with create_connection() as connection:
        with connection.cursor() as cursor:
            # Fetch posts related to the specified class
            sql = """
                SELECT posts.id, posts.content, posts.image, posts.user_id,
                       CONCAT(users.first_name, ' ', users.last_name) AS user_name,
                       classes.class_name
                FROM posts
                JOIN users ON posts.user_id = users.id
                JOIN classes ON posts.class_id = classes.id
                WHERE classes.id = %s
                """
            cursor.execute(sql, (class_id,))
            posts = cursor.fetchall()

            # Fetch class_name for header display
            sql = "SELECT class_name FROM classes WHERE id = %s"
            cursor.execute(sql, (class_id,))
            class_info = cursor.fetchone()
            class_name = class_info["class_name"] if class_info else None

            # Fetch all classes for dropdown
            sql = "SELECT id, class_name FROM classes"
            cursor.execute(sql)
            classes = cursor.fetchall()

            # Add like counts and comments to each post
            for post in posts:
                sql = "SELECT COUNT(*) FROM likes WHERE post_id = %s"
                cursor.execute(sql, (post['id'],))
                post['likes_count'] = cursor.fetchone()['COUNT(*)']

                sql = """SELECT comments.content, users.first_name, users.last_name, comments.created_at
                         FROM comments
                         JOIN users ON comments.user_id = users.id
                         WHERE comments.post_id = %s
                         ORDER BY comments.created_at DESC"""
                cursor.execute(sql, (post['id'],))
                post['comments'] = cursor.fetchall()

    return render_template('questify_post.html', class_id=class_id, classes=classes, posts=posts, class_name=class_name)



@app.route("/add_like/<int:post_id>", methods=["POST"])
def add_like(post_id):
    user_id = session.get("user_id")  
    current_class_id = session.get('current_class_id', None)

    if user_id:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "INSERT INTO likes (user_id, post_id) VALUES (%s, %s)"
                cursor.execute(sql, (user_id, post_id))
                connection.commit()

        return redirect(request.referrer)  # Redirect back to the same page
    else:
        return redirect(url_for('login'))

@app.route("/add_comment/<int:post_id>", methods=["POST"])
def add_comment(post_id):
    user_id = session.get("user_id")  
    current_class_id = session.get('current_class_id', None)
    content = request.form.get("content")  # Get comment content from the form

    if user_id:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "INSERT INTO comments (user_id, post_id, content) VALUES (%s, %s, %s)"
                cursor.execute(sql, (user_id, post_id, content))
                connection.commit()

        if current_class_id is not None:
            return redirect(url_for('class_posts', class_id=current_class_id))
        else:
            # Handle the case where current_class_id is not set
            return redirect(request.referrer)  # Redirect back to the same page
    else:
        return redirect(url_for('login'))






@app.route("/post/view/all")
def post_view_all():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """
                    SELECT * FROM posts 
                    LEFT JOIN users ON posts.user_id = users.id
                    """
            cursor.execute(sql)
            result = cursor.fetchall()
    return render_template("post_list.html", result=result)
# /update?id=1
@app.route("/update", methods=["GET", "POST"])
def update():
    if not can_access():
        flash("You don't have permission to do that!")
        return redirect("/")

    if request.method == "POST":
        with create_connection() as connection:
            with connection.cursor() as cursor:

                password = request.form["password"]
                if password:
                    encrypted_password = encrypt(password)
                else:
                    encrypted_password = request.form["old_password"]

                image = request.files["image"]
                if image:
                    # Choose a random filename to prevent clashes
                    ext = os.path.splitext(image.filename)[1]
                    image_path = "static/images/" + str(uuid.uuid4())[:8] + ext
                    image.save(image_path)
                    if request.form["old_image"]:
                        os.remove(request.form["old_image"])
                else:
                    image_path = request.form["old_image"]

                sql = """UPDATE users SET
                    first_name = %s,
                    last_name = %s,
                    email = %s,
                    password = %s,
                    birthday = %s,
                    image = %s
                    WHERE id = %s
                """
                values = (
                    request.form['first_name'],
                    request.form['last_name'],
                    request.form['email'],
                    encrypted_password,
                    request.form['birthday'],
                    image_path,
                    request.form['id']
                )
                cursor.execute(sql, values)
                connection.commit()
        return redirect("/")
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM users WHERE id = %s"
                values = (request.args["id"])
                cursor.execute(sql, values)
                result = cursor.fetchone()
        return render_template("update.html", result=result)

# /delete?id=1
@app.route("/delete")
def delete():
    if not can_access():
        flash("You don't have permission to do that!")
        return redirect("/")
    
    with create_connection() as connection:
        with connection.cursor() as cursor:
            # Get the image path before deleting the user
            sql = "SELECT image FROM users WHERE id = %s"
            values = (request.args["id"])
            cursor.execute(sql, values)
            result = cursor.fetchone()
            if result["image"]:
                os.remove(result["image"])

            sql = "DELETE FROM users WHERE id = %s"
            values = (request.args["id"])
            cursor.execute(sql, values)
            connection.commit()
    return redirect("/")

# /checkemail?email=a@a
@app.route("/checkemail")
def check_email():
    return {
        "exists": email_exists(request.args["email"])
    }

# /admin?id=1&role=admin
@app.route("/admin")
def toggle_admin():
    if "logged_in" in session and session["role"] == "admin":
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "UPDATE users SET role = %s WHERE id = %s"
                values = (
                    request.args["role"],
                    request.args["id"]
                )
                cursor.execute(sql, values)
                connection.commit()
    else:
        flash("You don't have permission to do that!")
    return redirect("/")

@app.route("/hidden")
def admin_only():
    return "Here is where I would put restricted content, if I had any."

if __name__ == '__main__':
    app.run()
app.run(debug=True)
