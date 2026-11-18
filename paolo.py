import os
import re
import html
import sqlite3
import smtplib
import ssl
from datetime import date
from email.message import EmailMessage
from functools import wraps
from io import BytesIO

from flask import (
    Flask, abort, flash, redirect, render_template_string,
    request, session, url_for, send_file
)
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False



app = Flask(__name__)
app.secret_key = os.environ.get(
    "ACADEMY_SECRET_KEY", "change-this-secret-key"
)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "academy_web.db")
PASS_MARK = 75
ACADEMY_GMAIL = os.environ.get("ACADEMY_GMAIL", "tontonryota@gmail.com").strip()
ACADEMY_GMAIL_APP_PASSWORD = os.environ.get("ACADEMY_GMAIL_APP_PASSWORD", "nafv ptjl qssr kzjg").replace(" ", "").strip()



LESSONS = [
    {
        "title": "Introduction to Programming",
        "description": "Learn what programming is and how Python works.",
        "body": """Programming is the process of writing instructions that a computer can follow.

Python is a high-level, interpreted, general-purpose programming language created by Guido van Rossum. It is known for readable syntax and is used in automation, websites, data science, and many other fields.

Key ideas:
• An algorithm is a step-by-step solution to a problem.
• A program is a set of instructions.
• Python code is executed by an interpreter.
• Popular tools include PyCharm, VS Code, and IDLE."""
    },
    {
        "title": "Python Basic Syntax",
        "description": "Understand statements, comments, and indentation.",
        "body": """Python syntax is the set of rules for writing valid Python code.

Example:
print("Hello, world!")

Key ideas:
• print() displays output.
• Comments begin with #.
• Python is case-sensitive.
• Indentation groups statements into code blocks.
• Use clear names and consistent spacing."""
    },
    {
        "title": "Variables and Data Types",
        "description": "Store information and identify common data types.",
        "body": """A variable is a named place to store a value.

Examples:
name = "Alex"
age = 18
price = 19.5
is_ready = True

Common data types:
• int – whole numbers
• float – decimal numbers
• str – text
• bool – True or False

Use type(value) to check a value's type."""
    },
    {
        "title": "Arithmetic Operators and Expressions",
        "description": "Work with calculations and expressions.",
        "body": """Arithmetic operators perform mathematical calculations.

• + addition
• - subtraction
• * multiplication
• / division
• // floor division
• % remainder (modulo)
• ** exponentiation

Python follows the usual order of operations. Use parentheses to make expressions clearer. Convert input using int() or float() before numeric calculations."""
    },
    {
        "title": "Basic Input and Output",
        "description": "Receive user input and display results.",
        "body": """Input and output allow a program to communicate with a user.

Example:
name = input("Enter your name: ")
print("Hello", name)

Key ideas:
• input() waits for the user to enter information.
• input() returns text (str), even when digits are entered.
• print() displays values and messages.
• Use int() or float() to convert numeric input."""
    },
    {
        "title": "Conditional Statements",
        "description": "Make decisions with if, elif, and else.",
        "body": """Conditional statements let a program choose which code to run.

Example:
score = 85
if score >= 75:
    print("Passed")
else:
    print("Try again")

Use if for the first condition, elif for additional conditions, and else for the fallback.

Comparison operators include ==, !=, >, <, >=, and <=."""
    },
    {
        "title": "Logical Operators",
        "description": "Combine conditions using and, or, and not.",
        "body": """Logical operators combine or reverse Boolean conditions.

• and – True when both conditions are True.
• or – True when at least one condition is True.
• not – reverses a Boolean value.

Example:
age = 20
has_id = True
if age >= 18 and has_id:
    print("Access allowed")

Logical operators are commonly used with if and while statements."""
    },
    {
        "title": "Introduction to Loops",
        "description": "Repeat instructions using for and while.",
        "body": """Loops repeat a block of code.

• for loops iterate over a sequence or range.
• while loops repeat while a condition is True.
• range(n) generates numbers from 0 up to (but not including) n.
• break exits a loop.
• continue skips to the next iteration.

Example:
for number in range(3):
    print(number)

Choose a loop based on the kind of repetition required."""
    }
]



QUESTIONS = [
    (
        "Which statement best describes programming?",
        ["Writing instructions for a computer", "Repairing a monitor",
         "Browsing the internet", "Designing a keyboard"],
        0,
        "Programming means creating instructions a computer can execute."
    ),
    (
        "Who created Python?",
        ["Bill Gates", "Guido van Rossum", "Dennis Ritchie", "James Gosling"],
        1,
        "Guido van Rossum created Python."
    ),
    (
        "Which function displays output in Python?",
        ["input()", "type()", "print()", "int()"],
        2,
        "print() displays text or values."
    ),
    (
        "Which symbol starts a Python comment?",
        ["//", "/*", "#", "--"],
        2,
        "A hash symbol (#) starts a single-line Python comment."
    ),
    (
        "Which data type stores whole numbers?",
        ["str", "int", "float", "bool"],
        1,
        "int represents whole numbers."
    ),
    (
        "What is the data type of 3.14?",
        ["int", "str", "float", "bool"],
        2,
        "A number with a decimal part is a float."
    ),
    (
        "What does the % operator return?",
        ["Quotient", "Remainder", "Power", "Product"],
        1,
        "Modulo (%) returns the remainder after division."
    ),
    (
        "Which operator means exponentiation?",
        ["//", "**", "%%", "^^"],
        1,
        "The ** operator raises a number to a power."
    ),
    (
        "Which function gets input from a user?",
        ["print()", "input()", "range()", "type()"],
        1,
        "input() reads text entered by the user."
    ),
    (
        "What does input() return by default?",
        ["int", "float", "str", "bool"],
        2,
        "input() returns a string."
    ),
    (
        "Which keyword begins a conditional statement?",
        ["for", "if", "def", "return"],
        1,
        "if begins a conditional statement."
    ),
    (
        "Which keyword checks another condition?",
        ["elif", "loop", "next", "case"],
        0,
        "elif checks another condition if earlier conditions were False."
    ),
    (
        "Which operator requires both conditions to be True?",
        ["or", "not", "and", "in"],
        2,
        "and is True only when both conditions are True."
    ),
    (
        "What does not do?",
        ["Adds values", "Reverses a Boolean value",
         "Repeats a loop", "Prints output"],
        1,
        "not reverses True to False and False to True."
    ),
    (
        "Which loop commonly iterates over a range?",
        ["for", "if", "else", "elif"],
        0,
        "A for loop is commonly used with range()."
    ),
    (
        "What does break do inside a loop?",
        ["Restarts the program", "Exits the loop",
         "Skips one line", "Pauses the computer"],
        1,
        "break immediately exits the current loop."
    )
]



def get_db():
    con = sqlite3.connect(DATABASE)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    """
    Creates the database and upgrades older versions where
    the email column was required.
    """

    con = sqlite3.connect(DATABASE, isolation_level=None)

    try:
        con.execute("PRAGMA foreign_keys=OFF")
        con.execute("BEGIN IMMEDIATE")

        existing = con.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='users'
        """).fetchone()

        if not existing:
            con.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    xp INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
        else:
            columns = con.execute(
                "PRAGMA table_info(users)"
            ).fetchall()

            email_column = next(
                (column for column in columns
                 if column[1] == "email"),
                None
            )

            if email_column and email_column[3] == 1:
                con.execute("""
                    CREATE TABLE users_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT UNIQUE,
                        username TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        xp INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL
                    )
                """)

                con.execute("""
                    INSERT INTO users_new
                    (id, name, email, username, password_hash, xp, created_at)
                    SELECT id, name, email, username, password_hash, xp, created_at
                    FROM users
                """)

                con.execute("DROP TABLE users")
                con.execute("ALTER TABLE users_new RENAME TO users")

        con.execute("""
            CREATE TABLE IF NOT EXISTS lesson_progress (
                user_id INTEGER NOT NULL,
                lesson_id INTEGER NOT NULL,
                completed_at TEXT NOT NULL,
                PRIMARY KEY (user_id, lesson_id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                correct INTEGER NOT NULL,
                total INTEGER NOT NULL,
                taken_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        con.execute("COMMIT")

    except Exception:
        con.execute("ROLLBACK")
        raise

    finally:
        con.execute("PRAGMA foreign_keys=ON")
        con.close()


def current_user():
    if "user_id" not in session:
        return None

    with get_db() as con:
        return con.execute(
            "SELECT * FROM users WHERE id=?",
            (session["user_id"],)
        ).fetchone()


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Please log in first.")
            return redirect(url_for("login"))

        return func(*args, **kwargs)

    return wrapper



BASE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }} | Python Academy</title>

<style>
:root{
    --bg:#100709;
    --panel:#1c0c11;
    --red:#b51e32;
    --gold:#f0c65f;
    --cream:#fff2df;
    --muted:#c7aeb1;
    --line:#67303b;
    --green:#58d49a;
}

*{box-sizing:border-box}

body{
    margin:0;
    background:radial-gradient(
        ellipse at 50% 0%,
        #47111c,
        #18090e 48%,
        #0c0608
    );
    color:#fff7ee;
    font:15px Arial,sans-serif;
    line-height:1.55;
    min-height:100vh;
}

a{
    color:var(--gold);
    text-decoration:none;
}

a:hover{
    text-decoration:underline;
    color:#fff1c5;
}

.topbar{
    min-height:66px;
    background:#10070bf5;
    border-bottom:1px solid #a43b49;
    display:flex;
    align-items:center;
    justify-content:space-between;
    padding:12px 4%;
    position:sticky;
    top:0;
    z-index:10;
}

.brand{
    font-weight:900;
    letter-spacing:1px;
    font-size:18px;
    color:#fff;
}

.brand b{color:var(--gold)}

.logo{
    display:inline-grid;
    place-items:center;
    width:36px;
    height:36px;
    border-radius:10px;
    background:linear-gradient(145deg,#f3c75f,#a66b19);
    color:#371017;
    font-weight:900;
    margin-right:9px;
}

.toplinks{
    display:flex;
    gap:14px;
    flex-wrap:wrap;
}

.toplinks a{
    font-size:13px;
    color:#f7e8dc;
    font-weight:bold;
}

.shell{
    display:flex;
    max-width:1450px;
    margin:auto;
    min-height:calc(100vh - 66px);
}

.sidebar{
    width:205px;
    flex-shrink:0;
    background:#16080cf2;
    border-right:1px solid #55212c;
    padding:22px 13px;
}

.userbox{
    text-align:center;
    padding:8px 4px 18px;
    border-bottom:1px solid #48202a;
    margin-bottom:14px;
}

.avatar{
    width:70px;
    height:70px;
    border-radius:50%;
    display:grid;
    place-items:center;
    margin:0 auto 9px;
    background:linear-gradient(145deg,#f7d47c,#9e2335);
    border:3px solid var(--gold);
    font-size:32px;
}

.userbox strong{display:block}
.userbox small{color:var(--gold)}

.side-links{
    display:grid;
    gap:6px;
}

.side-links a{
    padding:9px 10px;
    border-radius:8px;
    color:#e7d2ce;
    font-size:13px;
    font-weight:bold;
}

.side-links a:hover{
    background:linear-gradient(90deg,#8e1728,#4b101b);
    color:white;
    text-decoration:none;
}

.main{
    flex:1;
    min-width:0;
    padding:30px clamp(15px,3vw,42px) 55px;
}

.container{
    max-width:1120px;
    margin:auto;
}

h1{
    font-size:30px;
    line-height:1.2;
    margin:0 0 10px;
    color:var(--cream);
}

h2{
    color:var(--cream);
    margin:0 0 12px;
}

h3{
    color:var(--gold);
    margin:0 0 10px;
}

.muted{color:var(--muted)}
.small{font-size:12px}

.hero{
    position:relative;
    overflow:hidden;
    border:1px solid #c05b62;
    border-radius:18px;
    padding:32px;
    background:linear-gradient(
        112deg,#4d0d1a,#a71d31 58%,#58101d
    );
    box-shadow:0 14px 36px #0007;
    margin-bottom:20px;
}

.hero h1{font-size:34px}

.hero p{
    max-width:650px;
    color:#f6dfe0;
}

.card{
    background:linear-gradient(145deg,#2a1119,#1b0c11);
    border:1px solid #64303b;
    border-radius:15px;
    padding:21px;
    margin:14px 0;
    box-shadow:0 10px 24px #0004;
}

.grid{
    display:grid;
    grid-template-columns:repeat(
        auto-fit,minmax(205px,1fr)
    );
    gap:14px;
}

.stat{
    font-size:29px;
    font-weight:900;
    color:var(--gold);
    line-height:1.2;
    margin:5px 0;
}

.btn,button{
    display:inline-block;
    border:1px solid #e5b84f;
    border-radius:9px;
    padding:11px 17px;
    background:linear-gradient(135deg,#f6d16b,#c18b2e);
    color:#2b1013;
    font-weight:900;
    cursor:pointer;
    font-size:14px;
    margin:5px 5px 5px 0;
}

.btn:hover,button:hover{
    filter:brightness(1.08);
    text-decoration:none;
    color:#241014;
}

.btn.red{
    background:linear-gradient(135deg,#c62c42,#781323);
    border-color:#e15b6b;
    color:white;
}

.btn.dark{
    background:#392029;
    border-color:#72404a;
    color:white;
}

.field{
    display:block;
    width:100%;
    padding:13px;
    margin:7px 0 15px;
    background:#12080c;
    border:1px solid #693744;
    border-radius:8px;
    color:white;
    font-size:15px;
}

label{
    font-weight:bold;
    font-size:13px;
    color:#f2ded5;
}

.progress{
    height:12px;
    background:#4c2b34;
    border-radius:20px;
    overflow:hidden;
}

.progress span{
    display:block;
    height:100%;
    background:linear-gradient(90deg,#c21f39,#f4ca61);
    border-radius:20px;
}

.flash{
    padding:12px 15px;
    border:1px solid #b74455;
    background:#401722;
    border-radius:9px;
    margin:0 0 14px;
}

.option{
    display:block;
    padding:12px;
    margin:9px 0;
    background:#180b10;
    border:1px solid #60313c;
    border-radius:9px;
}

.option input{
    accent-color:#d22b43;
    margin-right:8px;
}

table{
    width:100%;
    border-collapse:collapse;
}

th,td{
    padding:12px;
    text-align:left;
    border-bottom:1px solid #57303a;
}

th{
    color:var(--gold);
    background:#35151e;
}

pre{
    white-space:pre-wrap;
    background:#12090d;
    border:1px solid #59303a;
    border-radius:9px;
    padding:18px;
    color:#f6dce0;
    overflow-wrap:anywhere;
}

.auth-wrap{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:20px;
    align-items:stretch;
    max-width:900px;
    margin:22px auto;
}

.auth-art{
    border-radius:18px;
    padding:30px;
    display:flex;
    flex-direction:column;
    justify-content:center;
    align-items:center;
    text-align:center;
    background:radial-gradient(
        circle at 50% 45%,#a7253b,#3d0c17 72%
    );
    border:1px solid #9d3948;
    min-height:440px;
}

.pylogo{font-size:82px}

.auth-art h1{
    font-size:34px;
    color:#ffe4a0;
}

.auth-card{
    margin:0;
    align-self:center;
    width:100%;
}

.certificate-preview{
    background:#fbf4e7;
    color:#4b1722;
    border:9px double #bd984e;
    outline:2px solid #781d30;
    outline-offset:5px;
    padding:36px 20px;
    text-align:center;
    margin:15px 5px 25px;
}

.certificate-preview .school{
    color:#8a2638;
    font-family:Georgia,serif;
    font-size:19px;
    font-weight:bold;
    letter-spacing:4px;
}

.certificate-preview .certificate-title{
    color:#8a2638;
    font-family:Georgia,serif;
    font-size:38px;
    font-weight:bold;
    letter-spacing:3px;
    margin:22px 0 0;
}

.certificate-preview .subtitle{
    color:#a17a36;
    font-family:Georgia,serif;
    font-size:17px;
    letter-spacing:5px;
}

.certificate-preview .student{
    color:#681a2b;
    font-family:Georgia,serif;
    font-size:34px;
    font-style:italic;
    font-weight:bold;
    overflow-wrap:anywhere;
    margin:15px 0;
}

.certificate-preview p{
    color:#61434a;
}

.certificate-preview .score{
    color:#8a2638;
    font-family:Georgia,serif;
    font-size:19px;
    font-weight:bold;
}

footer{
    text-align:center;
    color:#9f858a;
    padding:22px;
    border-top:1px solid #48202a;
    font-size:12px;
}

@media(max-width:800px){
    .sidebar{
        width:165px;
        padding:14px 8px;
    }
    .main{padding:20px 14px}
}

@media(max-width:620px){
    .topbar{
        align-items:flex-start;
        flex-direction:column;
        gap:8px;
    }

    .toplinks{gap:10px}

    .shell{display:block}

    .sidebar{
        width:100%;
        border-right:0;
        border-bottom:1px solid #55212c;
        padding:9px;
    }

    .userbox{display:none}

    .side-links{
        display:flex;
        overflow-x:auto;
    }

    .side-links a{white-space:nowrap}

    .main{padding:17px 12px}

    .auth-wrap{grid-template-columns:1fr}

    .auth-art{min-height:190px}

    .pylogo{font-size:54px}

    .hero{padding:22px}

    .hero h1{font-size:27px}

    h1{font-size:25px}

    .card{padding:16px}

    .certificate-preview{
        padding:25px 12px;
    }

    .certificate-preview .certificate-title{
        font-size:27px;
    }

    .certificate-preview .student{
        font-size:25px;
    }
}
</style>
</head>

<body>

<header class="topbar">
    <div class="brand">
        <span class="logo">Py</span>
        PYTHON <b>ACADEMY</b>
    </div>

    <div class="toplinks">
        {% if user %}
            <a href="{{ url_for('dashboard') }}">Dashboard</a>
            <a href="{{ url_for('lessons') }}">Lessons</a>
            <a href="{{ url_for('quiz') }}">Quiz</a>
            <a href="{{ url_for('leaderboard') }}">Leaderboard</a>
            <a href="{{ url_for('certificates') }}">Certificates</a>
            <a href="{{ url_for('logout') }}">Log out</a>
        {% else %}
            <a href="{{ url_for('login') }}">Login</a>
            <a href="{{ url_for('signup') }}">Sign Up</a>
        {% endif %}
    </div>
</header>

<div class="shell">

{% if user %}
<aside class="sidebar">
    <div class="userbox">
        <div class="avatar">👨🏻‍💻</div>
        <strong>{{ user['name'] }}</strong>
        <small>Python Student</small>

        <div class="progress" style="margin-top:10px">
            <span style="width:{{ [user['xp'] % 1000 / 10,100]|min }}%"></span>
        </div>

        <small>{{ user['xp'] }} XP</small>
    </div>

    <nav class="side-links">
        <a href="{{ url_for('dashboard') }}">Dashboard</a>
        <a href="{{ url_for('lessons') }}">My Lessons</a>
        <a href="{{ url_for('history') }}">Quiz History</a>
        <a href="{{ url_for('achievements') }}">Achievements</a>
        <a href="{{ url_for('leaderboard') }}">Leaderboard</a>
        <a href="{{ url_for('profile') }}">Profile</a>
        <a href="{{ url_for('certificates') }}">Certificates</a>
    </nav>
</aside>
{% endif %}

<main class="main">
    <div class="container">

        {% with messages = get_flashed_messages() %}
            {% for message in messages %}
                <div class="flash">{{ message }}</div>
            {% endfor %}
        {% endwith %}

        {{ content|safe }}

    </div>
</main>
</div>

<footer>
    PYTHON ACADEMY • ACT102 FUNDAMENTALS OF PROGRAMMING
    • LEARN • PRACTICE • ACHIEVE
</footer>

</body>
</html>
"""


def page(title, content):
    return render_template_string(
        BASE_TEMPLATE,
        title=title,
        content=content,
        user=current_user()
    )



@app.route("/")
def home():
    if current_user():
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not name or not username or len(password) < 8:
            flash("Enter your name and username. Password must be at least 8 characters.")

        elif not re.fullmatch(r"[^@\s]+@gmail\.com", email, re.I):
            flash("Enter a valid Gmail address. It will be used for login and certificates.")

        else:
            try:
                with get_db() as con:
                    con.execute("""
                        INSERT INTO users
                        (name,email,username,password_hash,created_at)
                        VALUES(?,?,?,?,?)
                    """, (
                        name,
                        email,
                        username,
                        generate_password_hash(password),
                        date.today().isoformat()
                    ))

                flash("Account created. You can now log in.")
                return redirect(url_for("login"))

            except sqlite3.IntegrityError:
                flash("That username or email is already registered.")

    content = """
    <div class="auth-wrap">

        <section class="auth-art">
            <div class="pylogo">🐍</div>
            <h1>PYTHON ACADEMY</h1>
            <p>Learn • Practice • Achieve</p>
            <p>Your coding journey starts here.</p>
        </section>

        <div class="card auth-card">
            <h1>Create Account</h1>
            <p class="muted">
                Join Python Academy and track your learning.
            </p>

            <form method="post">

                <label>Full name</label>
                <input class="field" name="name" required>

                <label>Gmail address</label>
                <input class="field" type="email" name="email"
                       placeholder="yourname@gmail.com" required>

                <label>Username</label>
                <input class="field" name="username"
                       placeholder="Choose a username" required>

                <label>Password (at least 8 characters)</label>
                <input class="field" type="password"
                       name="password" minlength="8" required>

                <button type="submit">Create account</button>

            </form>

            <p class="muted">
                Already registered? <a href="/login">Log in</a>
            </p>
        </div>
    </div>
    """

    return page("Sign up", content)


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        login_id = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with get_db() as con:
            found = con.execute(
                "SELECT * FROM users WHERE username=? OR lower(email)=?",
                (login_id, login_id.lower())
            ).fetchone()

        if found and check_password_hash(
            found["password_hash"], password
        ):
            session.clear()
            session["user_id"] = found["id"]

            return redirect(url_for("dashboard"))

        flash("Incorrect username/Gmail or password.")

    content = """
    <div class="auth-wrap">

        <section class="auth-art">
            <div class="pylogo">🐍</div>
            <h1>PYTHON ACADEMY</h1>
            <p>Learn • Practice • Achieve</p>
            <p>Welcome to your coding journey.</p>
        </section>

        <div class="card auth-card">
            <h1>Welcome Back!</h1>
            <p class="muted">
                Log in to continue your journey.
            </p>

            <form method="post">

                <label>Username or Gmail address</label>
                <input class="field" name="username"
                       placeholder="Your username or yourname@gmail.com" required>

                <label>Password</label>
                <input class="field" type="password"
                       name="password" required>

                <button type="submit">Log in</button>

            </form>

            <p class="muted">
                New student? <a href="/signup">Create an account</a>
            </p>
        </div>
    </div>
    """

    return page("Log in", content)


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have logged out.")
    return redirect(url_for("login"))



@app.route("/dashboard")
@login_required
def dashboard():

    u = current_user()

    with get_db() as con:
        completed = con.execute(
            "SELECT COUNT(*) FROM lesson_progress WHERE user_id=?",
            (u["id"],)
        ).fetchone()[0]

        attempts = con.execute(
            "SELECT COUNT(*) FROM attempts WHERE user_id=?",
            (u["id"],)
        ).fetchone()[0]

        best = con.execute(
            "SELECT MAX(score) FROM attempts WHERE user_id=?",
            (u["id"],)
        ).fetchone()[0] or 0

    percent = int(completed / len(LESSONS) * 100)
    safe_name = html.escape(u["name"])

    content = f"""
    <section class="hero">
        <p style="color:#ffe2a2;font-weight:bold">
            YOUR PYTHON JOURNEY
        </p>

        <h1>Welcome back, {safe_name}!</h1>

        <p>
            Keep learning, complete your lessons,
            and unlock your next achievement.
        </p>

        <a class="btn" href="/lessons">Continue learning</a>
    </section>

    <div class="grid">

        <div class="card">
            <div class="muted">Lessons completed</div>
            <div class="stat">{completed}/8</div>
        </div>

        <div class="card">
            <div class="muted">Course progress</div>
            <div class="stat">{percent}%</div>
        </div>

        <div class="card">
            <div class="muted">Quiz attempts</div>
            <div class="stat">{attempts}</div>
        </div>

        <div class="card">
            <div class="muted">Best quiz score</div>
            <div class="stat">{best}%</div>
        </div>

        <div class="card">
            <div class="muted">Experience points</div>
            <div class="stat">{u['xp']} XP</div>
        </div>

    </div>

    <div class="card">
        <h2>Overall course progress</h2>

        <div class="progress">
            <span style="width:{percent}%"></span>
        </div>

        <p class="muted">
            {completed} of 8 lessons completed.
        </p>
    </div>
    """

    return page("Dashboard", content)



@app.route("/lessons")
@login_required
def lessons():

    u = current_user()

    with get_db() as con:
        rows = con.execute(
            "SELECT lesson_id FROM lesson_progress WHERE user_id=?",
            (u["id"],)
        ).fetchall()

    completed = {r["lesson_id"] for r in rows}

    cards = ""

    for i, item in enumerate(LESSONS):
        status = (
            "✓ Completed"
            if i in completed
            else "Not completed"
        )

        cards += f"""
        <div class="card">

            <p class="muted">LESSON {i + 1:02d}</p>

            <h2>{html.escape(item['title'])}</h2>

            <p class="muted">
                {html.escape(item['description'])}
            </p>

            <p style="color:var(--gold)">{status}</p>

            <a class="btn" href="/lesson/{i}">
                Open lesson
            </a>

        </div>
        """

    content = """
    <section class="hero">
        <h1>Python Lessons</h1>
        <p>Learn the fundamentals, one topic at a time.</p>
    </section>
    <div class="grid">
    """ + cards + "</div>"

    return page("Lessons", content)


@app.route("/lesson/<int:lesson_id>", methods=["GET", "POST"])
@login_required
def lesson(lesson_id):

    if lesson_id < 0 or lesson_id >= len(LESSONS):
        abort(404)

    u = current_user()
    item = LESSONS[lesson_id]

    if request.method == "POST":

        with get_db() as con:
            result = con.execute("""
                INSERT OR IGNORE INTO lesson_progress
                (user_id,lesson_id,completed_at)
                VALUES(?,?,?)
            """, (
                u["id"],
                lesson_id,
                date.today().isoformat()
            ))

            if result.rowcount:
                con.execute(
                    "UPDATE users SET xp=xp+20 WHERE id=?",
                    (u["id"],)
                )

        flash("Lesson marked as completed.")

        return redirect(
            url_for("lesson", lesson_id=lesson_id)
        )

    with get_db() as con:
        done = con.execute("""
            SELECT 1 FROM lesson_progress
            WHERE user_id=? AND lesson_id=?
        """, (
            u["id"],
            lesson_id
        )).fetchone()

    body = html.escape(item["body"])
    title = html.escape(item["title"])
    description = html.escape(item["description"])

    previous_button = ""

    if lesson_id > 0:
        previous_button = (
            f'<a class="btn dark" href="/lesson/{lesson_id - 1}">'
            'Previous lesson</a>'
        )

    if lesson_id < len(LESSONS) - 1:
        next_button = (
            f'<a class="btn" href="/lesson/{lesson_id + 1}">'
            'Next lesson</a>'
        )
    else:
        next_button = (
            '<a class="btn" href="/quiz">Go to final quiz</a>'
        )

    completed_message = ""

    if done:
        completed_message = (
            '<p style="color:var(--green)">'
            'You have completed this lesson.</p>'
        )

    content = f"""
    <p class="muted">
        <a href="/lessons">All lessons</a>
        / Lesson {lesson_id + 1} of 8
    </p>

    <div class="card">

        <p class="muted">LESSON {lesson_id + 1:02d}</p>

        <h1>{title}</h1>

        <p class="muted">{description}</p>

        <pre>{body}</pre>

        {completed_message}

        <form method="post">
            <button type="submit" {'disabled' if done else ''}>
                {'Completed' if done else 'Mark as completed'}
            </button>
        </form>

        <p>
            {previous_button}
            {next_button}
        </p>

    </div>
    """

    return page(item["title"], content)



@app.route("/quiz", methods=["GET", "POST"])
@login_required
def quiz():

    u = current_user()

    with get_db() as con:
        completed = con.execute(
            "SELECT COUNT(*) FROM lesson_progress WHERE user_id=?",
            (u["id"],)
        ).fetchone()[0]

    if completed < len(LESSONS):
        flash("Complete all 8 lessons before taking the final quiz.")
        return redirect(url_for("lessons"))

    if request.method == "POST":

        correct = 0
        review_rows = []

        for i, question in enumerate(QUESTIONS):

            raw = request.form.get(f"q{i}")

            try:
                selected = int(raw)
            except (TypeError, ValueError):
                selected = -1

            is_correct = selected == question[2]

            if is_correct:
                correct += 1

            review_rows.append(
                (question, selected, is_correct)
            )

        score = round(
            correct / len(QUESTIONS) * 100
        )

        with get_db() as con:

            con.execute("""
                INSERT INTO attempts
                (user_id,score,correct,total,taken_at)
                VALUES(?,?,?,?,?)
            """, (
                u["id"],
                score,
                correct,
                len(QUESTIONS),
                date.today().isoformat()
            ))

            con.execute(
                "UPDATE users SET xp=xp+? WHERE id=?",
                (correct * 5, u["id"])
            )

        session["last_review"] = [
            {
                "question": q[0],
                "options": q[1],
                "answer": q[2],
                "explanation": q[3],
                "selected": selected,
                "correct": ok
            }
            for q, selected, ok in review_rows
        ]

        session["last_score"] = score

        return redirect(url_for("quiz_result"))

    question_html = ""

    for i, q in enumerate(QUESTIONS):

        options = ""

        for j, option in enumerate(q[1]):

            options += f"""
            <label class="option">
                <input type="radio"
                       name="q{i}"
                       value="{j}"
                       required>
                {chr(65 + j)}. {html.escape(option)}
            </label>
            """

        question_html += f"""
        <div class="card">
            <h3>{i + 1}. {html.escape(q[0])}</h3>
            {options}
        </div>
        """

    content = f"""
    <section class="hero">
        <p style="color:#ffe2a2;font-weight:bold">
            FINAL CHALLENGE
        </p>

        <h1>Final Quiz</h1>

        <p>
            Test your knowledge with 16 multiple-choice questions.
            You need 75% to pass.
        </p>
    </section>

    <div class="card">
        <strong>16 Questions</strong>
        &nbsp; • &nbsp;
        <strong>75% Passing Score</strong>
    </div>

    <form method="post">
        {question_html}
        <button type="submit">Submit final quiz</button>
    </form>
    """

    return page("Final Quiz", content)


@app.route("/quiz/result")
@login_required
def quiz_result():

    score = session.get("last_score")

    if score is None:
        return redirect(url_for("quiz"))

    passed = score >= PASS_MARK

    certificate_button = ""

    if passed:
        certificate_button = (
            '<a class="btn" href="/certificates">'
            'View certificate</a>'
        )

    content = f"""
    <div class="card" style="text-align:center">

        <p class="muted">QUIZ RESULT</p>

        <div class="stat" style="font-size:58px">
            {score}%
        </div>

        <h1>
            {"Congratulations! You passed." if passed
             else "Keep practicing!"}
        </h1>

        <p>
            {"Your certificate is now available."
             if passed
             else "You need at least 75% to pass. Review the explanations and try again."}
        </p>

        <a class="btn" href="/quiz/review">Review answers</a>

        {certificate_button}

        <a class="btn dark" href="/dashboard">Dashboard</a>

    </div>
    """

    return page("Quiz Results", content)


@app.route("/quiz/review")
@login_required
def quiz_review():

    rows = session.get("last_review")

    if not rows:
        flash("Take the quiz first to see your answer review.")
        return redirect(url_for("quiz"))

    content = """
    <h1>Answer Review</h1>
    <p class="muted">
        Check the correct answers and explanations.
    </p>
    """

    for i, item in enumerate(rows, 1):

        selected = item["selected"]
        correct_answer = item["answer"]

        selected_text = (
            item["options"][selected]
            if 0 <= selected < len(item["options"])
            else "No answer"
        )

        correct_text = item["options"][correct_answer]

        color = (
            "var(--green)"
            if item["correct"]
            else "#ff7b86"
        )

        content += f"""
        <div class="card">

            <h3>{i}. {html.escape(item['question'])}</h3>

            <p style="color:{color}">
                Your answer: {html.escape(selected_text)}
            </p>

            <p>
                Correct answer:
                <strong>{html.escape(correct_text)}</strong>
            </p>

            <p class="muted">
                {html.escape(item['explanation'])}
            </p>

        </div>
        """

    return page("Answer Review", content)



@app.route("/history")
@login_required
def history():

    u = current_user()

    with get_db() as con:
        rows = con.execute("""
            SELECT score,correct,total,taken_at
            FROM attempts
            WHERE user_id=?
            ORDER BY id DESC
        """, (u["id"],)).fetchall()

    if not rows:

        content = """
        <div class="card">
            <h2>No quiz attempts yet</h2>
            <p class="muted">
                Your quiz history will appear here.
            </p>
        </div>
        """

    else:

        table = """
        <div class="card">
        <table>
            <tr>
                <th>Date</th>
                <th>Score</th>
                <th>Correct</th>
                <th>Status</th>
            </tr>
        """

        for r in rows:

            status = (
                "Passed"
                if r["score"] >= PASS_MARK
                else "Try again"
            )

            table += f"""
            <tr>
                <td>{r['taken_at']}</td>
                <td>{r['score']}%</td>
                <td>{r['correct']}/{r['total']}</td>
                <td>{status}</td>
            </tr>
            """

        content = table + "</table></div>"

    return page(
        "Quiz History",
        "<h1>Quiz History</h1>" + content
    )



@app.route("/leaderboard")
@login_required
def leaderboard():

    with get_db() as con:
        rows = con.execute("""
            SELECT name,xp
            FROM users
            ORDER BY xp DESC,name ASC
            LIMIT 20
        """).fetchall()

    table = """
    <div class="card">
    <table>
        <tr>
            <th>Rank</th>
            <th>Student</th>
            <th>XP</th>
        </tr>
    """

    for i, row in enumerate(rows, 1):

        table += f"""
        <tr>
            <td>#{i}</td>
            <td>{html.escape(row['name'])}</td>
            <td>{row['xp']}</td>
        </tr>
        """

    table += """
    </table>

    <p class="muted small">
        This leaderboard includes accounts registered
        in this database only.
    </p>
    </div>
    """

    return page(
        "Leaderboard",
        "<h1>Leaderboard</h1>" + table
    )



@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    u = current_user()

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()

        if not name:
            flash("Enter your name.")

        elif not re.fullmatch(r"[^@\s]+@gmail\.com", email, re.I):
            flash("Enter a valid Gmail address. It is used for login and certificates.")

        else:

            try:
                with get_db() as con:
                    con.execute("""
                        UPDATE users
                        SET name=?,email=?
                        WHERE id=?
                    """, (
                        name,
                        email,
                        u["id"]
                    ))

                flash("Profile updated.")
                return redirect(url_for("profile"))

            except sqlite3.IntegrityError:
                flash("That email is already registered.")

    u = current_user()

    safe_name = html.escape(u["name"])
    safe_email = html.escape(u["email"] or "")
    safe_username = html.escape(u["username"])

    content = f"""
    <div class="card" style="max-width:600px">

        <h1>My Profile</h1>

        <form method="post">

            <label>Full name</label>
            <input class="field"
                   name="name"
                   value="{safe_name}"
                   required>

            <label>Gmail address</label>
            <input class="field"
                   type="email"
                   name="email"
                   value="{safe_email}"
                   required>

            <label>Username</label>
            <input class="field"
                   value="{safe_username}"
                   disabled>

            <p class="muted small">
                Your account and progress are stored
                in a local database.
            </p>

            <button type="submit">Save profile</button>

        </form>

    </div>
    """

    return page("My Profile", content)



@app.route("/achievements")
@login_required
def achievements():

    u = current_user()

    with get_db() as con:

        lessons_done = con.execute("""
            SELECT COUNT(*)
            FROM lesson_progress
            WHERE user_id=?
        """, (u["id"],)).fetchone()[0]

        best = con.execute("""
            SELECT MAX(score)
            FROM attempts
            WHERE user_id=?
        """, (u["id"],)).fetchone()[0] or 0

        attempts = con.execute("""
            SELECT COUNT(*)
            FROM attempts
            WHERE user_id=?
        """, (u["id"],)).fetchone()[0]

    items = [
        ("🌟", "First Steps", "Create your student account", True),
        ("📚", "Lesson Learner", "Complete your first lesson", lessons_done >= 1),
        ("🎓", "Course Finisher", "Complete all eight lessons", lessons_done >= len(LESSONS)),
        ("🏆", "Quiz Beginner", "Submit your first final quiz", attempts >= 1),
        ("🥇", "Python Master", "Pass the final quiz with 75% or higher", best >= PASS_MARK),
        ("💯", "Perfect Score", "Earn 100% on the final quiz", best == 100)
    ]

    cards = ""

    for icon, title, desc, unlocked in items:

        display_icon = icon if unlocked else "🔒"

        status = "Unlocked" if unlocked else "Locked"

        color = (
            "var(--green)"
            if unlocked
            else "var(--muted)"
        )

        cards += f"""
        <div class="card" style="text-align:center">

            <div style="font-size:38px">{display_icon}</div>

            <h3>{title}</h3>

            <p class="muted small">{desc}</p>

            <strong style="color:{color}">
                {status}
            </strong>

        </div>
        """

    content = """
    <section class="hero">
        <h1>Achievements</h1>
        <p>Celebrate your progress as you learn Python.</p>
    </section>

    <div class="grid">
    """ + cards + "</div>"

    return page("Achievements", content)



def best_score(user_id):

    with get_db() as con:
        return con.execute("""
            SELECT MAX(score)
            FROM attempts
            WHERE user_id=?
        """, (user_id,)).fetchone()[0] or 0


def make_certificate(student_name, score):

    if not REPORTLAB_AVAILABLE:
        raise RuntimeError(
            "ReportLab is not installed. Run: pip install reportlab"
        )

    output = BytesIO()

    pdf = canvas.Canvas(
        output,
        pagesize=landscape(A4)
    )

    width, height = landscape(A4)

    pdf.setFillColor(HexColor("#FBF5E9"))
    pdf.rect(0, 0, width, height, fill=1, stroke=0)

    pdf.setStrokeColor(HexColor("#BD984E"))
    pdf.setLineWidth(7)
    pdf.rect(
        22, 22,
        width - 44,
        height - 44,
        fill=0,
        stroke=1
    )

    pdf.setStrokeColor(HexColor("#781D30"))
    pdf.setLineWidth(2)
    pdf.rect(
        35, 35,
        width - 70,
        height - 70,
        fill=0,
        stroke=1
    )

    pdf.setStrokeColor(HexColor("#BD984E"))
    pdf.setLineWidth(1)

    pdf.line(125, height - 115, width - 125, height - 115)
    pdf.line(125, 115, width - 125, 115)

    pdf.setFillColor(HexColor("#781D30"))
    pdf.setFont("Times-Bold", 18)
    pdf.drawCentredString(
        width / 2,
        height - 100,
        "P Y T H O N   A C A D E M Y"
    )

    pdf.setFillColor(HexColor("#741D30"))
    pdf.setFont("Times-Bold", 38)
    pdf.drawCentredString(
        width / 2,
        height - 175,
        "CERTIFICATE"
    )

    pdf.setFillColor(HexColor("#A17A36"))
    pdf.setFont("Times-Roman", 17)
    pdf.drawCentredString(
        width / 2,
        height - 202,
        "O F   C O M P L E T I O N"
    )

    pdf.setFillColor(HexColor("#62454A"))
    pdf.setFont("Times-Italic", 15)
    pdf.drawCentredString(
        width / 2,
        height - 250,
        "This certificate is proudly presented to"
    )

    safe_student_name = student_name[:45]

    pdf.setFillColor(HexColor("#781D30"))
    pdf.setFont("Times-BoldItalic", 32)
    pdf.drawCentredString(
        width / 2,
        height - 305,
        safe_student_name
    )

    pdf.setStrokeColor(HexColor("#BD984E"))
    pdf.setLineWidth(1)
    pdf.line(
        width / 2 - 190,
        height - 315,
        width / 2 + 190,
        height - 315
    )

    pdf.setFillColor(HexColor("#62454A"))
    pdf.setFont("Times-Roman", 14)
    pdf.drawCentredString(
        width / 2,
        height - 355,
        "For successfully passing the ACT102 Python Academy final quiz."
    )

    pdf.setFillColor(HexColor("#781D30"))
    pdf.setFont("Times-Bold", 18)
    pdf.drawCentredString(
        width / 2,
        height - 395,
        f"FINAL QUIZ SCORE: {score}%"
    )

    pdf.setFillColor(HexColor("#62454A"))
    pdf.setFont("Times-Roman", 12)
    pdf.drawCentredString(
        width / 2,
        82,
        f"Issued on {date.today().strftime('%B %d, %Y')}"
    )

    pdf.save()
    output.seek(0)

    return output


@app.route("/certificates")
@login_required
def certificates():

    u = current_user()
    score = best_score(u["id"])

    if score >= PASS_MARK:

        safe_name = html.escape(u["name"])
        registered_email = html.escape(u["email"] or "")

        content = f"""
        <div class="card">

            <div class="certificate-preview">

                <div class="school">
                    PYTHON ACADEMY
                </div>

                <div class="certificate-title">
                    CERTIFICATE
                </div>

                <div class="subtitle">
                    OF COMPLETION
                </div>

                <p>
                    This certificate is proudly presented to
                </p>

                <div class="student">
                    {safe_name}
                </div>

                <p>
                    For successfully passing the
                    ACT102 Python Academy final quiz.
                </p>

                <div class="score">
                    FINAL QUIZ SCORE: {score}%
                </div>

                <p>
                    Issued on {date.today().strftime('%B %d, %Y')}
                </p>

            </div>

            <p style="text-align:center">
                <a class="btn" href="/certificate.pdf">
                    Download Certificate
                </a>
            </p>

        </div>

        <div class="card">

            <h2>Email Your Certificate</h2>

            <p class="muted small">
                Your certificate will be sent to your registered Gmail:
                <strong>{registered_email or "No Gmail saved"}</strong>.
            </p>

            <form method="post" action="/certificate/send">
                <label>Gmail address to receive the certificate</label>
                <input class="field" type="email" name="recipient_email"
                       value="{registered_email}" placeholder="Enter your Gmail address" required>
                <button type="submit">Send Certificate to Gmail</button>
            </form>

            <p class="muted small">
                The Academy sends certificates using its configured Gmail account.
                You only need to provide the Gmail address where you want to receive your certificate.
            </p>

        </div>
        """

    else:

        content = f"""
        <div class="card">

            <h1>Certificate Locked</h1>

            <p>
                Your best score is {score}%.
                You need at least {PASS_MARK}% to unlock
                your certificate.
            </p>

            <a class="btn" href="/quiz">
                Take Final Quiz
            </a>

        </div>
        """

    return page("Certificates", content)


@app.route("/certificate.pdf")
@login_required
def certificate_pdf():

    u = current_user()
    score = best_score(u["id"])

    if score < PASS_MARK:
        abort(403)

    if not REPORTLAB_AVAILABLE:
        flash("Install ReportLab using: pip install reportlab")
        return redirect(url_for("certificates"))

    output = make_certificate(u["name"], score)

    safe_name = re.sub(
        r"[^A-Za-z0-9_-]+",
        "",
        u["name"]
    ).strip("_") or "student"

    return send_file(
        output,
        as_attachment=True,
        download_name=f"Python_Academy_Certificate_{safe_name}.pdf",
        mimetype="application/pdf"
    )


@app.route("/certificate/send", methods=["POST"])
@login_required
def send_certificate():

    u = current_user()
    score = best_score(u["id"])

    if score < PASS_MARK:
        abort(403)

    if not REPORTLAB_AVAILABLE:
        flash("Install ReportLab using: pip install reportlab")
        return redirect(url_for("certificates"))

    sender = ACADEMY_GMAIL.lower()
    app_password = ACADEMY_GMAIL_APP_PASSWORD
    recipient = request.form.get("recipient_email", "").strip().lower()

    if not re.fullmatch(r"[^@\s]+@gmail\.com", sender, re.I) or not app_password:
        flash("The Academy Gmail sender is not configured. Please contact the administrator.")
        return redirect(url_for("certificates"))

    if not re.fullmatch(r"[^@\s]+@gmail\.com", recipient, re.I):
        flash("Enter a valid Gmail address to receive your certificate.")
        return redirect(url_for("certificates"))

    message = EmailMessage()

    message["Subject"] = "Your Python Academy Certificate"
    message["From"] = sender
    message["To"] = recipient

    message.set_content(
        f"""Hello {u['name']},

Congratulations on passing the ACT102 Python Academy final quiz!

Your certificate is attached to this email.

Final quiz score: {score}%

Python Academy
"""
    )

    try:

        pdf = make_certificate(u["name"], score)

        safe_name = re.sub(
            r"[^A-Za-z0-9_-]+",
            "",
            u["name"]
        ).strip("_") or "student"

        message.add_attachment(
            pdf.read(),
            maintype="application",
            subtype="pdf",
            filename=f"Python_Academy_Certificate_{safe_name}.pdf"
        )

        context = ssl.create_default_context()

        with smtplib.SMTP(
            "smtp.gmail.com",
            587,
            timeout=30
        ) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(sender, app_password)
            server.send_message(message)

        flash(
            f"Certificate successfully sent to your registered Gmail: {recipient}."
        )

    except smtplib.SMTPAuthenticationError:
        flash(
            "Gmail rejected the Academy sender login. The administrator must check "
            "the Academy Gmail and its Google App Password. Make sure 2-Step Verification is enabled."
        )

    except smtplib.SMTPRecipientsRefused:
        flash(
            "The recipient email address was rejected. "
            "Check the recipient address."
        )

    except (smtplib.SMTPException, OSError, TimeoutError) as exc:
        flash(
            f"Email could not be sent ({type(exc).__name__}). "
            "Check your internet connection and Gmail settings."
        )

    except Exception as exc:
        flash(
            f"Certificate email failed ({type(exc).__name__})."
        )

    return redirect(url_for("certificates"))



if __name__ == "__main__":

    init_db()

    print("\n===================================")
    print("          PYTHON ACADEMY")
    print("===================================")
    print("Open on this computer: http://127.0.0.1:5000")
    print("For phone access, use your computer's local IP address.")
    print("Keep this program running while using the website.")
    print("Sign in with your username OR registered Gmail address.")
    print("===================================\n")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
