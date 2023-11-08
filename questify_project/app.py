# Import necessary libraries and modules
import pymysql
import hashlib
import uuid
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import time


#dsjfnsdkfskfsdjfnskfsfn skfsfbzskfzbsdfszfbzskfbsfseb
#new word hahahahaaha


app = Flask(__name__)

# Allow flask to encrypt the session cookie.
app.secret_key = "any-random-string-reshrdjtfkygluvchfjkhlbh"
socketio = SocketIO(app)
# Function to create a connection to the database
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

# Function to check if a user can access certain resources
def can_access():
    if "logged_in" in session:
        matching_id = session["id"] == int(request.args["id"])
        is_admin = session["role"] == "admin"
        return matching_id or is_admin
    else:
        return False
# Function to encrypt passwords
def encrypt(password):
    return hashlib.sha256(password.encode()).hexdigest()
# Function to check if an email already exists in the database
def email_exists(email):
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users WHERE email = %s"
            values = (email)
            cursor.execute(sql, values)
            result = cursor.fetchone()
    return result is not None

# Function that runs before every page request to load necessary classes
@app.before_request
def load_classes_for_layout():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT id, class_name FROM classes"
            cursor.execute(sql)
            g.classes = cursor.fetchall()

# Route to render the page for admin
@app.route("/home")
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

# Route to render the home page with user and class information
@app.route("/")
def q_home():
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users"
            cursor.execute(sql)
            users = cursor.fetchall()

            # Fetching the classes
            sql = "SELECT id, class_name FROM classes"
            cursor.execute(sql)
            classes = cursor.fetchall()

    return render_template("questify_going_in.html", result=users, classes=classes)  # passing the classes to the template

# Route for login functionality
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Handling user login, validating credentials against the database
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
            
            return redirect("/questify")
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


# Route for logout, clears the session
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# Route to handle user signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    # Handling user registration and adding user details to the database
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
                session["user_id"] = result["id"]

        return redirect("/questify")
    else:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT id, class_name FROM classes"
                cursor.execute(sql)
                classes = cursor.fetchall()
        return render_template('signup.html', classes=classes)





# Route to view details of a user specified by id
@app.route("/view")
def view():
    # Creating a database connection
    with create_connection() as connection:
        with connection.cursor() as cursor:
            # SQL query to fetch user details based on id
            sql = "SELECT * FROM users WHERE id = %s"
            values = (request.args["id"])
            cursor.execute(sql, values)
            result = cursor.fetchone()
    # Rendering the view page with user details
    return render_template("view.html", result=result)


# Route to save an uploaded image and return the path
@app.route("/save-image", methods=["POST"])
def save_image():
    image = request.files["image"]
    if image:
        # Saving the uploaded image with a random filename
        ext = os.path.splitext(image.filename)[1]
        image_path = "static/images/" + str(uuid.uuid4())[:8] + ext
        image.save(image_path)
        image_path = "/" + image_path
    else:
        image_path = None
    # Returning the path of the saved image
    return { "default": image_path }



# Route to view details of a post specified by id
@app.route("/post")
def post():
    # Creating a database connection
    with create_connection() as connection:
        with connection.cursor() as cursor:
            # SQL query to fetch post details along with user information based on post id
            sql = """SELECT * FROM posts
                    LEFT JOIN users ON posts.user_id = users.id
                    WHERE posts.id = %s"""
            values = (request.args["id"])
            cursor.execute(sql, values)
            result = cursor.fetchone()
    # Rendering the post view page with post details
    return render_template("post_view.html", result=result)

from werkzeug.utils import secure_filename

from flask import redirect
from PIL import Image

# Route to add a new post
@app.route("/post/add", methods=["GET", "POST"])
def add_post():
    if request.method == "POST":
        # Handling the submission of a new post and saving it to the database
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
        
        return redirect(url_for('class_posts', class_id=class_id))

    else:
        # Rendering the add post page with class information
        with create_connection() as connection:
            with connection.cursor() as cursor:
                sql = "SELECT id, class_name FROM classes"
                cursor.execute(sql)
                classes = cursor.fetchall()
        return render_template("post_add.html", classes=classes)
        
# Function to calculate the time difference between the current time and a given timestamp
def time_since_posted(timestamp):
    now = datetime.now()  # Get the current date and time
    diff = now - timestamp  # Calculate the difference between current time and timestamp
    seconds = diff.total_seconds()  # Convert the difference into seconds
    
    # Determine and return a human-readable string based on the calculated time difference
    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    elif seconds < 3600:
        return f"{int(seconds // 60)} minutes ago"
    elif seconds < 86400:
        return f"{int(seconds // 3600)} hours ago"
    else:
        return f"{int(seconds // 86400)} days ago"
    


# SocketIO event listener for receiving messages
@socketio.on('send_message')
def handle_message(data):
    # Code for handling the received message and emitting it to the specified room
    print("Received message:", data)  # Debug line
    room = data['room']
    class_id = get_class_id_from_name(room)

    # Use the user_id from the session for security
    user_id = session["id"]  

    message = data['message']

    # Store the received message in the database along with user details

    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """
                SELECT first_name, last_name, image
                FROM users 
                WHERE id = %s
            """
            cursor.execute(sql, (user_id,))
            user_data = cursor.fetchone()

    full_name = user_data['first_name'] + " " + user_data['last_name']

    # Emit the message with user details to the specified room
    profile_pic = user_data['image'] or "static/images/default.png"

    emit('message', {
        'message': message,
        'username': full_name,
        'profile_pic': profile_pic
    }, room=room)


# SocketIO event listener for joining a room
@socketio.on('join')
def on_join(data):
    room_name = data['room']# Get the room name from received data
    class_id = get_class_id_from_name(room_name) # Join the specified room
    join_room(room_name)

    # Fetch the last 10 messages for this room from the database
    with create_connection() as connection:
        with connection.cursor() as cursor:
            # SQL query to fetch the last 10 messages for the room along with user details
            sql = """
                SELECT chat_messages.message, 
                       users.first_name, 
                       users.last_name, 
                       users.image
                FROM chat_messages 
                JOIN users ON chat_messages.user_id = users.id
                WHERE chat_messages.class_id = %s
                ORDER BY chat_messages.timestamp DESC LIMIT 10
            """
            cursor.execute(sql, (class_id,))
            messages = cursor.fetchall()
    # Emit the fetched messages to the room in chronological order
    for message in reversed(messages):
        if message:
            full_name = message['first_name'] + " " + message['last_name']
            profile_pic = message['image'] or "static/images/default.png"
            emit('message', {
                'message': message['message'], 
                'username': full_name, 
                'profile_pic': profile_pic
            })



# Route to display chat rooms that a user is part of
@app.route('/chat')
def chat_rooms_list():
    user_id = session['id']  # Get the user id from the session
    # Connect to the database and fetch the classes that the user is part of
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
    # Render the template and pass the user classes as context
    return render_template('questify_text.html', classes=user_classes)

# Route to display a specific chat room based on the class name
@app.route('/chat/<class_name>')
def chat_room_by_name(class_name):
    user_id = session['id']  # Get the user id from the session

    
    # Connect to the database and fetch the user's classes
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

    # Connect to the database and fetch the details of the specified class
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT class_name FROM classes WHERE class_name = %s LIMIT 1"
            cursor.execute(sql, (class_name,))
            current_class = cursor.fetchone()

    # Render the template and pass the class details as context
    return render_template('questify_text.html', classes=user_classes, current_class=current_class, user_id=user_id)



# Function to get the class id from its name
def get_class_id_from_name(class_name):
    # Connect to the database and fetch the id of the specified class
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT id FROM classes WHERE class_name = %s LIMIT 1"
            cursor.execute(sql, (class_name,))
            result = cursor.fetchone()
            if result:
                return result['id']
            else:
                return None  # Return None if the class doesn't exist


# Route to display posts in a Questify page
@app.route("/q_post")
def q_post():
    # Establishing a connection to the database
    with create_connection() as connection:
        with connection.cursor() as cursor:
            # SQL query to select necessary details about posts, users, and classes
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
    # Rendering the template with the posts as context
    return render_template("questify_post.html", posts=posts)

# Route to display a specific class page based on class name
@app.route('/class_page/<class_name>')
def class_page(class_name):
    # Rendering the class page template with the class name as context
    return render_template('class_page.html', class_name=class_name)

# Route to display the Questify home page with classes and todos
@app.route("/questify")
def questify():
    if 'id' not in session:
        flash('Please log in to access this page.')
        return redirect(url_for('login'))

    user_id = session['id']

    # Fetch user's classes
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

    # Fetch user's todos
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = """
                SELECT todo_list.id, todo_list.task_description, todo_list.is_complete, classes.class_name 
                FROM todo_list
                LEFT JOIN classes ON todo_list.class_id = classes.id
                WHERE todo_list.user_id = %s
                ORDER BY todo_list.is_complete ASC, todo_list.id DESC
            """



            cursor.execute(sql, (user_id,))
            todos = cursor.fetchall()

    return render_template('questify_home.html', classes=user_classes, todos=todos)

# Route to add a new todo item
@app.route('/add_todo', methods=['POST'])
def add_todo():
    todo_text = request.form.get('text')
    todo_class_id = request.form.get('class_id')
    # Store in the database
    with create_connection() as connection:
        with connection.cursor() as cursor:
            sql = "INSERT INTO todo_list (user_id, class_id, task_description) VALUES (%s, %s, %s)"
            cursor.execute(sql, (session["id"], todo_class_id, todo_text))  # use session["id"] here
            connection.commit()

    # Redirect to the questify route to display the updated todos
    return redirect(url_for('questify'))

# Route to update the status of a todo item
@app.route('/update_todo_status', methods=['POST'])
def update_todo_status():
    data = request.json  # Getting the JSON data sent with the request
    todo_id = data.get('todo_id')  # Getting the id of the todo to be updated
    is_complete = data.get('is_complete')  # Getting the new completion status of the todo
    

    # Updating the todo's completion status in the database
    with create_connection() as connection:
        with connection.cursor() as cursor:
            # SQL query to update the todo's completion status
            sql = "UPDATE todo_list SET is_complete = %s WHERE id = %s"
            print("Executing SQL:", sql)  # debug print
            cursor.execute(sql, (is_complete, todo_id))
            connection.commit()

    return jsonify(success=True)

# Route to display the desktop version of the Questify home page
@app.route("/desktop")
def desktop():
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

    return render_template('questify_home_desktop.html', classes=user_classes)







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
                       classes.class_name, posts.created_at
                FROM posts
                JOIN users ON posts.user_id = users.id
                JOIN classes ON posts.class_id = classes.id
                WHERE classes.id = %s
                ORDER BY posts.created_at DESC
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
                sql = "SELECT COUNT(*) as like_count FROM likes WHERE post_id = %s"
                cursor.execute(sql, (post['id'],))
                post['likes_count'] = cursor.fetchone()['like_count']
                sql = "SELECT id FROM likes WHERE user_id = %s AND post_id = %s"
                cursor.execute(sql, (session.get("user_id"), post['id']))
                post['liked_by_user'] = bool(cursor.fetchone())  # This will be True if the user has liked the post, False otherwise

                sql = """SELECT comments.content, users.first_name, users.last_name, comments.created_at
                        FROM comments
                        JOIN users ON comments.user_id = users.id
                        WHERE comments.post_id = %s
                        ORDER BY comments.created_at DESC"""
                cursor.execute(sql, (post['id'],))
                post['comments'] = cursor.fetchall()

                post['time_since_posted'] = time_since_posted(post['created_at'])


            return render_template('questify_post.html', class_id=class_id, classes=classes, posts=posts, class_name=class_name)


@app.route("/add_like/<int:post_id>", methods=["POST"])
def add_like(post_id):
    user_id = session.get("user_id")  
    current_class_id = session.get('current_class_id', None)

    if user_id:
        with create_connection() as connection:
            with connection.cursor() as cursor:
                # Check if the like already exists
                sql = "SELECT id FROM likes WHERE user_id = %s AND post_id = %s"
                cursor.execute(sql, (user_id, post_id))
                existing_like = cursor.fetchone()

                if existing_like:
                    # If like exists, remove it
                    sql = "DELETE FROM likes WHERE id = %s"
                    cursor.execute(sql, (existing_like['id'],))
                else:
                    # If like doesn't exist, add it
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
    socketio.run(app, debug=True)


app.run(debug=True)

