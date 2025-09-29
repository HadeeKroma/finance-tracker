# app.py
from datetime import date
from collections import defaultdict
import os

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    current_user, login_required
)

# ----------------------------------
# App & DB config
# ----------------------------------
app = Flask(__name__)

# Local dev uses SQLite file; Render will also work with this unless you switch to Postgres
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///expenses.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# IMPORTANT: set a strong SECRET_KEY in production (Render env var)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-change-me')

db = SQLAlchemy(app)

# ----------------------------------
# Auth setup
# ----------------------------------
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # anonymous users are redirected here

# ----------------------------------
# Models
# ----------------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.String(10), default=lambda: date.today().strftime('%Y-%m-%d'))

    def set_password(self, pw: str):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw: str) -> bool:
        return check_password_hash(self.password_hash, pw)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date_added = db.Column(db.String(10), nullable=False)
    # Ownership
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('expenses', lazy=True))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----------------------------------
# Routes: Dashboard & Expense CRUD
# ----------------------------------
@app.route('/', methods=['GET'])
@login_required
def home():
    # Only show the current user's expenses
    all_expenses = (
        Expense.query.filter_by(user_id=current_user.id)
        .order_by(Expense.id.desc())
        .all()
    )
    total = sum(e.amount for e in all_expenses)

    # Group by category
    category_totals = defaultdict(float)
    for e in all_expenses:
        category_totals[e.category] += e.amount

    return render_template(
        'index.html',
        total=total,
        expenses=all_expenses,
        category_totals=dict(category_totals),
    )


@app.route('/add', methods=['POST'])
@login_required
def add_expense():
    description = request.form.get('description', '').strip()
    amount = float(request.form.get('amount') or 0)
    category = request.form.get('category', '').strip()
    date_added = request.form.get('date') or date.today().strftime('%Y-%m-%d')

    if not description or not category:
        flash('Description and Category are required.', 'warning')
        return redirect(url_for('home'))

    exp = Expense(
        description=description,
        amount=amount,
        category=category,
        date_added=date_added,
        user_id=current_user.id,
    )
    db.session.add(exp)
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/edit/<int:expense_id>', methods=['GET'])
@login_required
def edit_expense(expense_id):
    # Users can only edit their own expense
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    return render_template('edit.html', expense=expense)


@app.route('/edit/<int:expense_id>', methods=['POST'])
@login_required
def update_expense(expense_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    expense.description = request.form.get('description', '').strip()
    expense.amount = float(request.form.get('amount') or 0)
    expense.category = request.form.get('category', '').strip()
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for('home'))

# ----------------------------------
# Routes: Auth (login/register/logout)
# ----------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        pw = request.form.get('password') or ''

        if not email or not pw:
            flash('Email and password are required.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email is already registered.', 'warning')
            return redirect(url_for('register'))

        user = User(email=email)
        user.set_password(pw)
        db.session.add(user)
        db.session.commit()
        login_user(user)  # log them in right away
        return redirect(url_for('home'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        pw = request.form.get('password') or ''
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(pw):
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('login'))

        login_user(user, remember=True)
        return redirect(url_for('home'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ----------------------------------
# Entry point
# ----------------------------------
if __name__ == '__main__':
    # Create tables on first run (SQLite)
    with app.app_context():
        db.create_all()
    app.run(debug=True)
