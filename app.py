from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# ---------------- APP ---------------- #

app = Flask(__name__)
app.secret_key = os.urandom(24)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------- MODELS ---------------- #

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    priority = db.Column(db.String(10))
    due_date = db.Column(db.Date)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)

# ---------------- DB ---------------- #

with app.app_context():
    db.create_all()

# ---------------- ROUTES ---------------- #

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect('/login')

    search = request.args.get('search')
    filter_type = request.args.get('filter')

    tasks_query = Task.query.filter_by(user_id=session['user_id'])

    if search:
        tasks_query = tasks_query.filter(Task.title.contains(search))

    if filter_type == "completed":
        tasks_query = tasks_query.filter_by(completed=True)
    elif filter_type == "pending":
        tasks_query = tasks_query.filter_by(completed=False)

    tasks = tasks_query.all()

    return render_template('index.html', tasks=tasks)

# ---------------- ADD TASK ---------------- #
@app.route('/add', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        return redirect('/login')

    title = request.form['title']
    priority = request.form.get('priority')
    due_date = request.form.get('due_date')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')

    if title.strip():
        task = Task(
            title=title,
            priority=priority,
            due_date=datetime.strptime(due_date, "%Y-%m-%d") if due_date else None,
            start_time=datetime.strptime(start_time, "%H:%M").time() if start_time else None,
            end_time=datetime.strptime(end_time, "%H:%M").time() if end_time else None,
            user_id=session['user_id']
        )

        db.session.add(task)
        db.session.commit()

        flash("Task added successfully!", "success")

    return redirect('/')

# ---------------- DELETE ---------------- #

@app.route('/delete/<int:id>')
def delete_task(id):
    task = Task.query.get_or_404(id)

    if task.user_id != session.get('user_id'):
        return "Unauthorized"

    db.session.delete(task)
    db.session.commit()

    flash("Task deleted successfully!", "success")

    return redirect('/')

# ---------------- TOGGLE ---------------- #

@app.route('/toggle/<int:id>')
def toggle_task(id):
    task = Task.query.get_or_404(id)

    if task.user_id != session.get('user_id'):
        return "Unauthorized"

    task.completed = not task.completed
    db.session.commit()

    flash("Task updated!", "success")

    return redirect('/')

# ---------------- AUTH ---------------- #

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # ✅ VALIDATION
        if not username or not password:
            flash("All fields required", "error")

        elif User.query.filter_by(username=username).first():
            flash("Username already exists", "error")

        else:
            user = User(
                username=username,
                password=generate_password_hash(password)
            )
            db.session.add(user)
            db.session.commit()

            flash("Signup successful! Please login.", "success")
            return redirect('/login')

    return render_template('signup.html')

# ---------------- LOGIN ---------------- #

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id

            flash("Login successful!", "success")

            return redirect('/')
        else:
            flash("Invalid username or password", "error")

    return render_template('login.html')

# ---------------- LOGOUT ---------------- #

@app.route('/logout')
def logout():
    session.pop('user_id', None)

    flash("Logged out successfully", "success")

    return redirect('/login')

# ---------------- API ---------------- #

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    tasks = Task.query.filter_by(user_id=session['user_id']).all()

    return jsonify([
        {
            "id": t.id,
            "title": t.title,
            "completed": t.completed,
            "priority": t.priority,
            "due_date": str(t.due_date)
        }
        for t in tasks
    ])

# ---------------- RUN ---------------- #

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)