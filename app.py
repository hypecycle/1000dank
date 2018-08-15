import sqlite3
import os
import sys
import json
import random
from flask import Flask, render_template, redirect, url_for, request
from wtforms import Form, StringField, IntegerField, SubmitField
from wtforms.validators import Required
import logging
from logging.handlers import RotatingFileHandler



"""
1000dank.db

Tabelle Saetze 
------------------------------------------------
| Column | Typ         		  | Beschreib      |
------------------------------------------------
| Id     | NUMBER PRIMARY KEY | 0 … lfd nr.    |
| List   | TEXT               | Json dump Satz |
| Vari   | NUMBER             | Number Variati |


Tabelle Varianten
------------------------------------------------
| Column | Typ         		  | Beschreib      |
------------------------------------------------
| Id     | NUMBER PRIMARY KEY | 0 … lfd nr.    |
| Vari   | TEXT               | Plain txt      |
| Satznr | NUMBER             | Rel Saetze–ID  |
| Dorder | NUMBER             | Order 4Display |


internal dict{1: ['word'], 2 }

app.py conf json jandling, ready for deploy > FIRST COMMIT app.py
app.py 0.27 manually initiate BUGGY
app.py 0.28 setting up for internal, external use
app.py 0.29 cleaning up git glitches
app.py 0.30 lose session w/edit_8

"""

DBSCHEMA = """CREATE TABLE Saetze(
			  Id        NUMBER PRIMARY KEY, 
			  List      TEXT, 
			  Vari      NUMBER); 

			  CREATE TABLE Varianten(
			  Id        NUMBER PRIMARY KEY, 
			  Vari      TEXT,  
			  Satznr    NUMBER,
			  Dorder    NUMBER);
			  """

config = json.load(open('conf.json', 'r'))
SECRET_KEY = config['secret']
DBFILENAME = config['db']
DISPLAY_COUNTER = 0

# -------------------------- LOGGING defined -------------------------------

handler = RotatingFileHandler(config['log'], maxBytes=10000, backupCount=1)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

initial =  [
		{0:["Danke,", "Fein,", "Wie schön"],
         1: ["dass du"], 2: ["die Bücher", "deine Bücher"],
         3: ["in deinem BILLY", "in deinem IVAR"],
         4: ["jede Woche", "alle zwei Wochen"],
         5: ["umsortierst", "neu sortierst", "nach Farben sortierst"]},
        {0: ["Danke,", "Fein,", "Wie schön"], 1: ["dass du dein Sofa"],
         2: ["extra so gekauft hast"], 3: ["dass deine Freunde", "dass deine Eltern"],
         4: ["drauf schlafen können"]},
        {0: ["Supernett,", "Wie toll,", "fein"],
         1: ["dass du deine IKEA Küche", "dass du deinen Kühlschrank"],
         2: ["manchmal", "auch gern mal", "jedes Mal"],
         3: ["mitten in der Nacht", "um 3 Uhr"], 4: ["besuchst"]}
         ]


class neueAltern(Form):
	alterNeu = StringField('Text', validators=[Required()])
	sendButt = SubmitField(label='Sende')


# ------------------------ INITIAL creation and initial fill -------------------

def createDB(initial):
	"""Creates and inits DB. Needs DBFILENAME and DBSCHEMA as OSvars
	Needs list of sample dicts in var initial. Checks OS Path
	"""
	dbExists = os.path.exists(DBFILENAME)
	with sqlite3.connect(DBFILENAME) as conn:
		if not dbExists:
			print('Initiiere DB')
			conn.executescript(DBSCHEMA)
			initialFill(initial)
		else:
			print('DB existiert')

	return

def initialFill(initial):
	"""Called, if DB doesnt' exist yet
	Fills fresh DB with sample Data
	Needs Variable Initial passed.
	Careful: ID count starts at 1, Dict starts at 0
	"""
	with sqlite3.connect(DBFILENAME) as conn:
		cursor = conn.cursor()

		for i in range(len(initial)):
			cursor.execute("INSERT INTO Saetze VALUES (?, ?, ?)", (str(i), json.dumps(initial[i]), str(countVari(initial[i]))))
		print('DB filled with sample Data')
	return


def satzKeyToInt(satzOld):
	"""json module turns dict keys into strs.
	   Architecture expects keys as ints. So, this is for reformatting
	"""
	i = 0
	satzNew = {}

	for istr in satzOld:
		#print(satzSQ[istr])
		satzNew[i] = satzOld[istr]
		i += 1
	return(satzNew)


# ------------------------------- SATZ handling -------------------------------

def loadSatz(satzNr):
	with sqlite3.connect(DBFILENAME) as conn:
		cursor = conn.cursor()

		cursor.execute("SELECT List FROM Saetze WHERE Id = " + str(satzNr))

		rows = cursor.fetchall()

		for row in rows:
			satzSQ = json.loads(row[0])

		satzOK = satzKeyToInt(satzSQ)

	return(satzOK)


def updSatz(satzNew, satzNr):
	"""Writes a new Version of a sentence satzNew to row id satznr."""
	with sqlite3.connect(DBFILENAME) as conn:   
		cursor = conn.cursor()
		cursor.execute("UPDATE Saetze SET List = ?, Vari = ? WHERE Id = " + str(satzNr), (json.dumps(satzNew), str(countVari(satzNew))))
	return


def newSatz(satzNew, satzNr):
	"""Enters Data in a new row
	"""
	with sqlite3.connect(DBFILENAME) as conn:
		cursor = conn.cursor()
		cursor.execute("INSERT INTO Saetze VALUES (?, ?, ?)", (str(satzNr), json.dumps(satzNew), str(1)))
		print('New Satz created')
	return


def rowsSaetze():
	"""Getting the total number of lines in Satznr """
	with sqlite3.connect(DBFILENAME) as conn:
		cursor = conn.cursor()
		cursor.execute('SELECT Id FROM saetze ORDER BY Id DESC LIMIT 1')
		rows = cursor.fetchone()
	return rows[0]


# ---------------------- VARIATIONS/Alternative handling -----------------------

def buildVari():
	""" Loads every Satz, iterates variations and writes them 
	"""

	# Clean DB
	with sqlite3.connect(DBFILENAME) as conn:
		cursor = conn.cursor()
		cursor.execute("DELETE FROM Varianten")

	alleVaris= [[]]
	satzID = 0 # increment here

	for j in range(rowsSaetze() + 1):
		#loads each Satz
		satzLoaded = loadSatz(j)
		# Build a nested list of possible variations in Satz
		alleVaris= [[]]


		for satzteilNr in satzLoaded:
			builder = []
			for satzteil in satzLoaded[satzteilNr]:
				for vari in alleVaris:
					builder.append(vari+[satzteil])

			alleVaris = builder

		#print(alleVaris)
		#print(len(alleVaris))

		for variSaetze in alleVaris:
			satzNeu = ''
			for satzteil in variSaetze:
				if not satzNeu.endswith(' ') and not satzteil.startswith(' ') and not satzteil.startswith(',') and not len(satzNeu) == 0:
					satzNeu += ' '
				satzNeu += satzteil
			#print(satzNeu)
			with sqlite3.connect(DBFILENAME) as conn:
				cursor = conn.cursor()
				cursor.execute("INSERT INTO Varianten VALUES (?, ?, ?, ?)", (str(satzID), satzNeu, str(j), str(0)))
			satzID += 1
	return


def loadVari(satzNr):
	"""Loads the Variante with the given ID, Returns list w/ Satz + nr of Parent."""

	with sqlite3.connect(DBFILENAME) as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT Vari, Satznr FROM Varianten WHERE Id = " + str(satzNr))
		rows = cursor.fetchall()
	return rows[0][0], rows[0][1]


def loadVByOrd(satzNr):
	"""Loads the Variante with the given ID, Returns list w/ Satz + nr of Parent."""

	with sqlite3.connect(DBFILENAME) as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT Vari FROM Varianten WHERE Dorder = " + str(satzNr))
		rows = cursor.fetchall()
	return rows[0][0]


def countVari(satz):
	"""Calculates nr of variations of a given Satz """
	dataValues = []
	variations= 1
	for key, val in satz.items():
		dataValues.append(val)
		variations = variations*len(val)
	return variations


def sumVari():
	"""Returns sum of all varis in DB"""
	with sqlite3.connect(DBFILENAME) as conn:   
		cursor = conn.cursor()   
		cursor.execute("SELECT SUM (Vari) FROM Saetze;")
		rows = cursor.fetchall()
		vari = (rows[0][0])
	return(vari)


def calcMaxAltern(satz):
	""" Returns the max number of alternatives for the sentence for
	pretty row calc. Awaits Satz """
	maxAltern = 0
	for i in satz:
		length = len(satz[i])
		if maxAltern < length:
			maxAltern = length
	return maxAltern


# ------------------------------- DISPLAY functs  ------------------------------


def buildOrder():
	varis = sumVari()

	displayOrder = []

	for i in range(varis):
		displayOrder.append(i)

	random.shuffle(displayOrder)

	for i in range(varis):
		with sqlite3.connect(DBFILENAME) as conn:   
			cursor = conn.cursor()
			cursor.execute("UPDATE Varianten SET Dorder = ? WHERE Id = ?", (str(displayOrder[i]), str(i)))
	return


# ----------------------------- Edit calculations  -----------------------------


def calcFirstRow(satz):
	""" calc chars in first row of Satz for beautiful col-width """
	charsRow = []
	charsCount = 0
	charsCheck = 0
	for i in satz:
		charsCount += len(satz[i][0]) + 5
	charsCount += int(charsCount/len(satz)/3)

	for i in satz:
		charsPerc = int((100 / charsCount) * (len(satz[i][0]) + 5 ))
		charsRow.append(charsPerc)
		charsCheck += charsPerc
	charsRow.append(100 - charsCheck)
	return charsRow


def calcRowLastField (satz, fieldToAdd):
	""" calc chars in first row of Satz for col-width, enlarge column to add """
	charsRow = []
	charsCount = 0
	charsCheck = 0
	for i in satz:
		charsCount += len(satz[i][0]) + 5
	charsCount += int(charsCount/len(satz)/3)

	for i in satz:
		charsPerc = int((80 / charsCount) * (len(satz[i][0]) + 5 ))
		charsRow.append(charsPerc)
		charsCheck += charsPerc
		if 	fieldToAdd[0] == i:
			charsRow[fieldToAdd[0]] = charsRow[fieldToAdd[0]] * 1.5
	charsRow.append(100 - charsCheck)
	return charsRow


# ----------------------------- VIEW functions  -----------------------------


@app.route('/')
def edit():
	return "Start"

@app.route('/edit/<int:satznr>')
def edit_new(satznr):

	print(satznr)

	satz = loadSatz(satznr)

	app.logger.debug('Edit Satz Nr %d', satznr)

	return render_template('edit_8.html',
							satz = satz, 
							nr = satznr, 
							maxAltern = calcMaxAltern(satz),
							rows = rowsSaetze(),
							vari = countVari(satz),
							charsRow = calcFirstRow(satz),
							variSum = sumVari(),
							pageTitle = "Bearbeiten",
							baseURL = BASE_URL,
							)


@app.route('/addfield//<int:satznr>/<int:satzteilnr>/<int:alternatnr>', methods=['GET', 'POST'])
def addfield(satznr, satzteilnr, alternatnr):
	fieldToAdd = []
	fieldToAdd.append(satzteilnr)
	fieldToAdd.append(alternatnr)


	print(fieldToAdd)

	form = neueAltern(request.form)

	satz = loadSatz(satznr)

	if request.method == 'POST':
		alterNEnter=request.form['alterNeu']
		if len(satz) <= fieldToAdd[0]: # This is True, if new Satzteil is added
			satz[fieldToAdd[0]] = []
		satzToAdd = satz[satzteilnr] 
		satzToAdd.append(alterNEnter) # ??? Works by magic
		updSatz(satz, satznr)
		#print(satz)
		#print(alterNEnter)
		return redirect(url_for('edit_new', satznr = satznr))


	return render_template('addfield_2.html', 
							satz = satz, 
							nr = satznr, 
							maxAltern = calcMaxAltern(satz),
							rows = rowsSaetze(),
							vari = countVari(satz),
							variSum = sumVari(),
							charsRow = calcRowLastField(satz, fieldToAdd),
							form = form,
							fieldToAdd = fieldToAdd,
							pageTitle = "Erweitern",
							baseURL = BASE_URL,
							)

@app.route('/new', methods=['GET', 'POST'])
def new():
	satzToAdd = rowsSaetze() + 1
	form = neueAltern(request.form)


	if request.method == 'POST':
		satz = {}
		satz[1]= []
		vari=request.form['alterNeu']
		satz[1].append(vari)
		newSatz(satz, satzToAdd)
		app.logger.info('Created Satz Nr %d', satzToAdd)
		return redirect(url_for('edit_new', satznr = satzToAdd))


	return render_template('new_1.html', 
							rows = satzToAdd,
							form = form,
							variSum = sumVari(),
							pageTitle = "Neu",
							baseURL = BASE_URL,
							)


@app.route('/delete/<satznr>/<satzteilnr>/<alternatnr>')
def delete(satznr, satzteilnr, alternatnr):
	satzToDel = loadSatz(satznr)
	print(satzToDel)
	deleted = satzToDel.get(int(satzteilnr))
	deleted.pop(int(alternatnr))
	satzToDel[int(satzteilnr)] = deleted
	updSatz(satzToDel, satznr) # ??? updSatz is being popped, too. Works by magic 
	print(deleted)
	return redirect(url_for('edit_new', satznr = satznr))



@app.route('/build')
def build():
	"""Takes DB and builds every possible variation
	"""
	buildVari() # build DB of Variations
	buildOrder() # build, shuffle and write order to DB
	return redirect(url_for('edit_new', satznr = 0))


@app.route('/vari/<int:variNr>/<int:variPerPage>')
def vari(variNr, variPerPage):
	"""shows Variation
	"""
	#variNr = -1
	variPerPage = 10 # Entries per Page

	if variNr < 0:
		variNr = 0

	variMax = variNr + variPerPage
	print(sumVari())

	if variMax > sumVari():
		variMax = sumVari()

	varis = []
	for i in range(variNr, variMax):
		varis.append(loadVari(i))

	return render_template('vari_1.html',
							vari = varis, 
							variNr = variNr + 1,
							variMax = variMax + 1,
							variSum = sumVari(),
							pageTitle = "Varianten",
							baseURL = BASE_URL,
							)


@app.route('/display')
def display():
	"""Display new version each time func is called
	"""

	global DISPLAY_COUNTER

	if DISPLAY_COUNTER >= sumVari() -1:
		DISPLAY_COUNTER = 0
	else:
		DISPLAY_COUNTER += 1


	app.logger.debug('Display  message %d', DISPLAY_COUNTER)

	return render_template('display_2.html',
							displayText = loadVByOrd(DISPLAY_COUNTER),
							displayNr = DISPLAY_COUNTER,
							pageTitle = "Varianten",
							baseURL = BASE_URL,
							)

"""@app.route('/initial')
def initial():

	# Manually nitiate database and fill it with sample data
	createDB(initial)
	buildVari() # build DB of Variations
	buildOrder() # build, shuffle and write order to DB

	return redirect(url_for('edit'))"""


if __name__ == '__main__':
	BASE_URL = config['url_int']
	createDB(initial)
	buildVari() # build DB of Variations
	buildOrder() # build, shuffle and write order to DB
	app.run(debug=True)
else:
	# import libraries in lib directory
	base_path = os.path.dirname(__file__)
	sys.path.insert(0, os.path.join(base_path, 'lib'))

	BASE_URL = config['url_ext']
	createDB(initial)
	buildVari() # build DB of Variations
	buildOrder() # build, shuffle and write order to DB



