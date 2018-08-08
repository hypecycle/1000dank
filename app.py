import sqlite3
import os
import json
import random
from flask import Flask, render_template, redirect, url_for, session, request
from wtforms import Form, StringField, IntegerField, SubmitField
from wtforms.validators import Required



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

datastorage_6.py writing, fetching works
datastorage_7.py moving retrieve to funct 
datastorage_8.py moving to dict 
datastorage_9.py serve with flask – works with edit_1.html
datastorage_10.py serve with flask – works with edit_2.html
				  building index with text format. Delet started
datastorage_11.py works with edit_3.html – Careful: List popping works by accident
datastorage_12.py view_2.html tweaking view screen
datastorage_13.py view_3.html navigation
				  view_4.html for better format
datastorage_14.py view_4.html edit_4.html deleting
datastorage_14.py edit_4.html adding next row 
datastorage_15.py view_5 edit_5.html switching to container inst of table 
datastorage_16.py edit_6.html addfield_1.html wtf
datastorage_17.py edit_6.html addfield_1.html wtf populating add
datastorage_18.py edit_6.html addfield_1.html database rewritten as in 17f
datastorage_19.py edit_6.html addfield_1.html view_6.html new_1.html adding new set
datastorage_20.py edit_7.html losing view mode
datastorage_21.py edit_7.html Writing vas in DB
datastorage_22.py vari_1.py show vari
datastorage_23.py saving random.shuffle for display
datastorage_24.py tweaking internal display counter handling
datastorage_25.py improving view
datastorage_26.py conf json jandling, ready for deploy

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

config = json.load(open('conf.json', 'r+'))
BASE_URL = config['url']
SECRET_KEY = config['secret']
DBFILENAME = config['db']

DISPLAY_COUNTER = 0

session = {}
session['satzStore'] = 0


app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY


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

"""class jumpTo(Form):
	satzNr = IntegerField('Nummer', validators=[Required()])
	send = SubmitField('Senden')"""


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

# ------------------------ INITIAL creation and initial fill -------------------

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
	if session.get('satzStore'):
		satznr = session.get('satzStore')
	else:
		satznr = 0 # not jet handled in this session

	satz = loadSatz(satznr)

	return render_template('edit_7.html', 
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

@app.route('/addfield', methods=['GET', 'POST'])
def addfield():
	fieldToAdd = session['fieldAdd']
	print(fieldToAdd)
	form = neueAltern(request.form)

	satznr = session.get('satzStore')

	satz = loadSatz(satznr)

	if request.method == 'POST':
		alterNEnter=request.form['alterNeu']
		if len(satz) <= fieldToAdd[0]: # This is True, if new Satzteil is added
			satz[fieldToAdd[0]] = []
		satzToAdd = satz[fieldToAdd[0]] 
		satzToAdd.append(alterNEnter) # ??? Works by magic
		updSatz(satz, satznr)
		#print(satz)
		#print(alterNEnter)
		return redirect(url_for('edit'))


	return render_template('addfield_1.html', 
							satz = satz, 
							nr = satznr, 
							maxAltern = calcMaxAltern(satz),
							rows = rowsSaetze(),
							vari = countVari(satz),
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
		session['satzStore'] = int(satzToAdd)
		return redirect(url_for('edit'))


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
	return redirect(url_for('edit'))


@app.route('/addlink/<int:satznr>/<int:satzteilnr>/<int:alternatnr>')
def addlink(satznr, satzteilnr, alternatnr):
	session['fieldAdd'] = [satzteilnr, alternatnr]
	#session['fieldAdd'].append(satzteilnr)
	#session['fieldAdd'].append(alternatnr)
	return redirect(url_for('addfield'))	


@app.route('/navigate/<int:satznr>')
def navigate(satznr):
	if int(satznr) >= 0 and int(satznr) <= rowsSaetze(): 
		session['satzStore'] = int(satznr)
	return redirect(url_for('edit'))


@app.route('/build')
def build():
	"""Takes DB and builds every possible variation
	"""
	buildVari() # build DB of Variations
	buildOrder() # build, shuffle and write order to DB
	return redirect(url_for('edit'))


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


	return render_template('display_2.html',
							displayText = loadVByOrd(DISPLAY_COUNTER),
							displayNr = DISPLAY_COUNTER,
							pageTitle = "Varianten",
							baseURL = BASE_URL,
							)


if __name__ == '__main__':
	# Initiate database and fill it with sample data
	createDB(initial)
	buildVari() # build DB of Variations
	buildOrder() # build, shuffle and write order to DB
	app.run(debug=False)



