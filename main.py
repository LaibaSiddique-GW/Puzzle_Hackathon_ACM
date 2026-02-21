from flask import Flask, session, render_template, redirect, url_for, request
# import sqlite3
# import re
# import random
import string
# from datetime import datetime, timedelta 

app = Flask('app')
app.debug = True
app.secret_key = "CHANGE ME"

""" for reference 
connection = sqlite3.connect("myDatabase.db")
connection.row_factory = sqlite3.Row
cur = connection.cursor()
"""

# session key set up
app = Flask('app')
app.debug = True
app.secret_key = 'sessionKey'
app.config['SESSION_PERMANENT'] = False

