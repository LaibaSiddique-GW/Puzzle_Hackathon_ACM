# from flask import Flask, session, render_template, redirect, url_for, request
# # import sqlite3
# # import re
# # import random
# import string
# # from datetime import datetime, timedelta 

# app = Flask('app')
# app.debug = True
# app.secret_key = "CHANGE ME"

# """ for reference 
# connection = sqlite3.connect("myDatabase.db")
# connection.row_factory = sqlite3.Row
# cur = connection.cursor()
# """

# # session key set up
# app = Flask('app')
# app.debug = True
# app.secret_key = 'sessionKey'
# app.config['SESSION_PERMANENT'] = False


from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit, join_room
from game_state import GameState
import uuid

app = Flask(__name__, static_folder='../client', static_url_path='', template_folder='../client')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

sessions = {}  # session_id -> GameState

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/solo_level_1')
def solo_level_1():
    return render_template('solo_level_1.html')

@app.route('/api/start_game', methods=['POST'])
def start_game():
    data = request.get_json()
    mode = data.get('mode', 1)  # 1 or 2 players
    session_id = str(uuid.uuid4())[:8].upper()
    sessions[session_id] = GameState(session_id, num_players=mode)
    return jsonify({'session_id': session_id})

@app.route('/api/input', methods=['POST'])
def handle_input():
    data = request.get_json()
    session_id = data.get('session_id')
    inputs = data.get('inputs')  # dict: { "p1": {...}, "p2": {...} }

    if session_id not in sessions:
        return jsonify({'error': 'Session not found'}), 404

    state = sessions[session_id]
    for pid, inp in inputs.items():
        state.apply_input(pid, inp)
    state.update()

    result = state.serialize()
    result['win'] = state.check_win()
    return jsonify(result)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080, debug=True)

#  Add page for choosing single or multiplayer mode, and then redirect to game page with session id in URL.
# @app.route('/choose_mode')
# def choose_mode():
#     return render_template('choose_mode.html')
