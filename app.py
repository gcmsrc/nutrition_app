from flask import Flask, render_template, g, request
from datetime import datetime
import sqlite3
from database import connect_db, get_db

app = Flask(__name__)

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

@app.route('/', methods=['GET', 'POST'])
def index():

    db = get_db()

    if request.method == 'POST':
        date = request.form['date'] #assuming date is in format YYYY-MM-DD

        df = datetime.strptime(date, '%Y-%m-%d')
        database_date = df.strftime('%Y%m%d')

        db.execute('INSERT INTO log_date (entry_date) VALUES (?)', [database_date])
        db.commit()

    cur = db.execute('''SELECT log_date.entry_date,
	                        SUM(food.protein) protein,
	                        SUM(food.carbohydrates) carbohydrates,
	                        SUM(food.fat) fat,
                            SUM(food.calories) calories
                        FROM log_date 
                        LEFT JOIN food_date
                        ON food_date.log_date_id = log_date.id
                        LEFT JOIN food
                        ON food.id = food_date.food_id
                        GROUP BY log_date.id
                        ORDER BY log_date.entry_date DESC''')
    results = cur.fetchall()

    # Modify date format
    date_results = []
    for r in results:
        single_date = {}
        
        single_date['entry_date'] = r['entry_date']

        single_date['protein'] = r['protein']
        single_date['carbohydrates'] = r['carbohydrates']
        single_date['fat'] = r['fat']
        single_date['calories'] = r['calories']

        d = datetime.strptime(str(r['entry_date']), '%Y%m%d')
        single_date['pretty_date'] = d.strftime('%B %d, %Y')
        
        date_results.append(single_date)

    return render_template('home.html', results=date_results)

@app.route('/view/<date>', methods=['GET', 'POST']) #date is something like 20200415
def view(date):

    db = get_db()

    cur = db.execute('SELECT id, entry_date FROM log_date WHERE entry_date=?', [date])
    date_result = cur.fetchone()

    if request.method == 'POST':
        db.execute('INSERT INTO food_date (food_id, log_date_id) VALUES (?, ?)',\
            [request.form['food-select'], date_result['id']])
        db.commit()
        
    d = datetime.strptime(str(date_result['entry_date']), '%Y%m%d')
    pretty_date = d.strftime('%B %d, %Y')

    food_cur = db.execute('SELECT id, name FROM food ORDER BY name ASC')
    food_results  = food_cur.fetchall()

    log_cur = db.execute('''SELECT food.name, food.protein, food.carbohydrates, food.fat, food.calories from log_date 
                            JOIN food_date
                            ON food_date.log_date_id = log_date.id
                            JOIN food
                            ON food.id = food_date.food_id
                            WHERE log_date.entry_date = ?''', [date])
    log_results = log_cur.fetchall()

    # Calculate totals
    totals = {
        'protein' : 0,
        'carbohydrates' : 0,
        'fat' : 0,
        'calories' : 0
    }
    for food in log_results:
        totals['protein'] += food['protein']
        totals['carbohydrates'] += food['carbohydrates']
        totals['fat'] += food['fat']
        totals['calories'] += food['calories']

    return render_template('day.html',
                            entry_date=date, 
                            pretty_date=pretty_date,
                            food_results=food_results,
                            log_results=log_results,
                            totals=totals)

@app.route('/food', methods=['GET', 'POST'])
def food():

    db = get_db()

    if request.method == 'POST':

        name = request.form['food-name']
        protein = int(request.form['protein'])
        carbohydrates = int(request.form['carbohydrates'])
        fat = int(request.form['fat'])
        calories = int(protein * 4 + carbohydrates * 4 + fat * 9)

        db.execute('INSERT INTO food (name, protein, carbohydrates, fat, calories) VALUES (?, ?, ?, ?, ?)', \
            [name, protein, carbohydrates, fat, calories])
        db.commit()

    cur = db.execute('SELECT name, protein, carbohydrates, fat, calories FROM food')
    results = cur.fetchall()

    return render_template('add_food.html', results=results)

if __name__ == "__main__":
    app.run(debug=True)