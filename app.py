from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, make_response
from flask_socketio import SocketIO
import jwt
import mysql.connector
import datetime


app = Flask(__name__)
app.config['SECRET_KEY'] = 'myConfig'
socketio = SocketIO(app)


mydb = mysql.connector.connect(
    host='127.0.0.1',
    port=3306,
    user='csn',
    passwd='4252',
    database='chat'
)


@app.route('/')
def home():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():

    username = request.form['username']
    password = request.form['password']

    data = query_fetchone('SELECT * FROM user WHERE username ="' + username + '" and password="' + password + '"')

    if data:
        token = query_fetchall(f'SELECT token FROM user WHERE username="{username}"')[0]
        return redirect(url_for('chat', token=token))
    else:
        if request.form['username'] and request.form['password']:
            session['logged_in'] = True
            token = jwt.encode({
                'user': request.form['username'],
                'exp': datetime.datetime.max
            },
                app.config['SECRET_KEY']).decode('utf-8')

            insert_db('INSERT INTO user (username, password, token) VALUE (%s,%s,%s)', (username, password, token))

            return redirect(chat('addtoken', token=token))
        else:
            return make_response('Unable to verify', 403)


@socketio.on('send_message')
def handle_send_message_event(data):
    # data = [username, message, time]
    app.logger.info(f"{data['username']} has sent message: {data['message']}")

    username = data['username']
    message = data['message']
    time = data['time']

    insert_db('INSERT INTO history (username, message, time) VALUE (%s,%s,%s)', (username, message, time))

    socketio.emit('receive_message', data)


def check_token(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        token = request.args.get('token')
        if not token:
            return jsonify({'message': 'Missing token'}), 403
        try:
            jwt.decode(token, app.config['SECRET_KEY'])
        except:
            return jsonify({'message': 'Invalid Token'}), 403
        return func(*args, **kwargs)

    return wrapped


@app.route('/chat')
@check_token
def chat():
    token = request.args.get('token')

    username = query_fetchall(f'SELECT username FROM user WHERE token="{ token }"')[0]

    history = query_fetchall('SELECT * FROM history')

    print(history)

    return render_template('chat.html',
                           username=username,
                           history=history,
                           )


def query_fetchall(query):
    cursor = mydb.cursor()
    cursor.execute(query)
    result = cursor.fetchall()
    result = [i[0] if len(i) == 1 else i for i in result]
    return result


def query_fetchone(query):
    cursor = mydb.cursor(buffered=True)
    cursor.execute(query)
    result = cursor.fetchone()
    return result


def insert_db(insert, value):
    cursor = mydb.cursor()
    cursor.execute(insert, value)
    mydb.commit()


if __name__ == '__main__':
    socketio.run(app, debug=True)
