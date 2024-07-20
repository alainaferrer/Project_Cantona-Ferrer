from flask import Flask, render_template, url_for, redirect, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from sqlalchemy.exc import IntegrityError
from flask import Flask, request, render_template, flash, redirect, url_for, session
from subjective import SubjectiveQuestions
import os
import openai

app = Flask(__name__)
#openai.api_key = 'removed for safety'
app.config["SECRET_KEY"] = 'weregreat'
db = SQLAlchemy() # db intitialized here
bcrypt = Bcrypt(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#CLASSES
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(80), nullable=False)

with app.app_context():
    db.create_all()

class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Register')
    def validate_username(self, username):
        existing_user_username = User.query.filter_by(username=username.data).first()
        if existing_user_username:
            flash('That username already exists. Please choose a different one.')

class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Login')

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    due_date = db.Column(db.String(10))  # Store dates as strings for simplicity
    status = db.Column(db.String(20), nullable=False, default='pending')

with app.app_context():
    db.create_all()

class TaskForm(FlaskForm):
    title = StringField(validators=[InputRequired(), Length(min=1, max=100)], render_kw={"placeholder": "Task"})
    due_date = StringField(render_kw={"placeholder": "Due Date"})
    status = BooleanField('Completed')
    submit = SubmitField('Add Task')

class EditTaskForm(TaskForm):
    submit = SubmitField('Update Task')


#PAGES OF THE WEBSITE NA!
@app.route("/") #FIRST PAGE, leads to login/register
def hello():
    return render_template("hello.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash("Log in details are incorrect. Try again or register for an account")
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = (RegisterForm())
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        try:
            hashed_password = bcrypt.generate_password_hash(form.password.data)
            new_user = User(username=form.username.data, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')

    return render_template('register.html', form=form)


#WEBSITE-PROPER ONCE LOGGED IN
@app.route('/dashboard', methods=['GET', 'POST']) #offers redirects to others
@login_required
def dashboard():
    return render_template('dashboard.html')

#1ST PART OF WEBSITE: STUDY TIPS
@app.route('/studytips')
@login_required
def studytips():
    return render_template("studytips.html")

#2ND PART OF WEBSITE: TASKS ORGANIZER (view, add, edit, update status)
@app.route('/tasks', methods=['GET'])
@login_required
def view_tasks():
    tasks = Task.query.filter_by(user_id=current_user.id).filter(Task.status != 'completed').all()
    return render_template('tasks.html', tasks=tasks)

@app.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    form = TaskForm()
    if form.validate_on_submit():
        new_task = Task(
            title=form.title.data,
            due_date=form.due_date.data,
            status= "pending",
            user_id=current_user.id
        )
        db.session.add(new_task)
        db.session.commit()
        return redirect(url_for('view_tasks'))
    return render_template('add_task.html', form=form)

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        abort(403)

    form = EditTaskForm()
    if form.validate_on_submit():
        task.title = form.title.data
        task.due_date = form.due_date.data
        task.status = 'completed' if form.status.data else 'pending'
        db.session.commit()
        return redirect(url_for('view_tasks'))

    if request.method == 'GET':
        form.title.data = task.title
        form.due_date.data = task.due_date
        form.status.data = task.status == 'completed'

    return render_template('edit_task.html', form=form, task=task)

@app.route('/update_task_status', methods=['POST'])
@login_required
def update_task_status():
    task_ids = request.form.getlist('task_ids')
    tasks = Task.query.filter_by(user_id=current_user.id).all()

    for task in tasks:
        if str(task.id) in task_ids:
            task.status = 'completed'
        else:
            task.status = 'pending'

        if task.status == 'completed':
            db.session.delete(task)
        else:
            db.session.add(task)

    db.session.commit()
    return redirect(url_for('view_tasks'))


@app.route('/quiz')
def index():
    return render_template('index.html')


@app.route('/AnswerQuiz', methods=["POST"])
def quiz_generate():
    if request.method == "POST":
        inputText = request.form["itext"]
        generator = SubjectiveQuestions(inputText)
        question_list, answer_list = generator.generate_test()

        print(question_list)
        print(answer_list)

        session['answer_list'] = answer_list
        session['question_list'] = question_list

        return render_template('generatedquizdata.html', questions=question_list)


@app.route('/CheckQuiz', methods=["POST"])
def quiz_submit():
    user_answers = request.form.getlist('answers')
    questions = session.get('question_list', [])
    correct_answers = session.get('answer_list', [])

    print("Session Questions: ", questions)
    print("Session Answers: ", correct_answers)
    print("User Answers: ", user_answers)

    results = []
    for i in range(0, len(questions)):
        question = questions[i]
        user_ans = user_answers[i]
        corr_ans = correct_answers[i]
        sub_result = [question, user_ans, corr_ans]
        results.append(sub_result)

    print(results)

    return render_template('quiz_results.html', results=results)


@app.route('/QuizScore', methods=["POST"])
def quiz_score():
    questions = session.get('question_list', [])
    correct_answers = session.get('answer_list', [])

    results = request.form.getlist('results')
    correct_count = len(results)
    total_items = len(questions)

    score = int(correct_count / total_items * 100)
    if score == 0:
        message = "Look at me, this isn't you."


    elif 0 < score <= 10:
        message = "Grab a blanket and a cup of coffee because you need to study in Matteo Up All Night."

    elif 10 < score <= 20:
        message = "Your coins at the rock family might have made you lucky but they're not enough to make you ace your test."

    elif 20 < score <= 30:
        message = "Someone's been studying the basics. Keep it up, eagle!"

    elif 30 < score <= 40:
        message = "Burry yourself a bit more in the books of Rizal Library and you'll ace your test for sure!"

    elif 40 < score <= 50:
        message = "Almost halfway! Try a study date with your friend (or lover 😚) in IRH."

    elif 50 < score <= 60:
        message = "Over 50% of the material covered? Crazy! Go go go, eagle!"

    elif 60 < score <= 70:
        message = "You can debate with your Ateneo Debate Society friends about this already, but 80% chance you'll lose, so keep studying!"

    elif 70 < score <= 80:
        message = "Almost there! Decline Pop-up, Walrus, or Blackbox invites for now!"

    elif 80 < score <= 90:
        message = "High-scorer in the house! Patch up the knowledge gaps and the letter grade A is all yours."

    elif 90 < score < 100:
        message = "You're going to ace your test!"

    elif score == 100:
        message = "Tulog ka na, idol."

    return render_template('quiz_score.html', score=score, message=message)


#LOGOUT, LEADS BACK TO HOME PAGE
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return render_template("hello.html")

if __name__ == "__main__":
    app.run(debug=True)
