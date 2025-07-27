from datetime import date
from flask import Flask, render_template, request, redirect, url_for
from collections import defaultdict
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)


#COnfigure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#Initialize the database
db = SQLAlchemy(app)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date_added = db.Column(db.String(10), nullable=False)


# Global list to store expenses



@app.route('/', methods=['GET'])
def home():
    all_expenses = Expense.query.all()
    total = sum(e.amount for e in all_expenses)

    # Grouping expenses by category
    category_totals = defaultdict(float)
    for expense in all_expenses:
        category_totals[expense.category] += expense.amount
    return render_template('index.html', total=total, expenses=all_expenses, category_totals=dict(category_totals))

@app.route('/add', methods=['POST'])
def add_expense():
    description = request.form.get('description', ' ')
    amount = float(request.form.get('amount', 0))
    category = request.form.get('category', ' ')
    new_expense = Expense(
        description=description,
        amount=amount,
        category=category,
        date_added=date.today().strftime('%Y-%m-%d')
    )
    db.session.add(new_expense)
    db.session.commit()

    # Redirect to avoid form resubmission on refresh
    return redirect(url_for('home'))

@app.route('/edit/<int:expense_id>', methods=['GET'])
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    return render_template('edit.html', expense=expense)

@app.route('/delete/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    
    # Redirect to avoid form resubmission on refresh
    return redirect(url_for('home'))

@app.route('/update/<int:expense_id>', methods=['POST'])
def update_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    expense.description = request.form.get('description', ' ')
    expense.amount = float(request.form.get('amount', 0))
    expense.category = request.form.get('category', ' ')
    db.session.commit()
    
    # Redirect to avoid form resubmission on refresh
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)

