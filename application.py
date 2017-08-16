from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class

from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
import os
from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response


# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///tables.db")

# configure Flask-Uploads
photos = UploadSet("photos", IMAGES)
app.config['UPLOADED_PHOTOS_DEST'] = "static/uploads/img"
patch_request_class(app)
configure_uploads(app,photos)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("Missing username")
            
        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("Missing password")
            
        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1:
            return redirect(url_for("register"))
        if not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("Invalid username or password")
            
        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    
    # forget any user_id
    session.clear()

    # get form responses and store in variables
    if request.method == "POST":
        username = request.form.get("username")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        password = request.form.get("password")
        password_confirm = request.form.get("confirmation")
        
        # check if name form is blank
        if username == "":
            return apology("Missing username")
        elif first_name == "":
            return apology("Missing first name")
        elif last_name == "":
            return apology("Missing last name")
        elif password == "":
            return apology("Missing password")
        elif password_confirm == "":
            return apology("Missing password confirmation")
        
        # check that password matches password confirmation
        if password != password_confirm:
            return apology("Password and confirmation do not match")
        
        # hash password to encrypt it
        hashpwd = pwd_context.hash(password)
        
        # add user to database
        result = db.execute("INSERT INTO users (username,first_name,last_name,hash) VALUES (:username,:first_name,:last_name,:hashpwd)", username=username, first_name=first_name, last_name=last_name, hashpwd=hashpwd)
        if not result:
            return apology("Username already exists")
        
        # continue to personal info page
        session["user_id"] = result
        return redirect(url_for("personalinfo"))
        
    elif request.method == "GET":
        return render_template("register.html")

@app.route("/personalinfo", methods=["GET","POST"])
@login_required
def personalinfo():
    
    # if method is GET, display personal info page, otherwise store data
    if request.method == "GET":
        return render_template("personalInfo.html")
    elif request.method =="POST":
        
        # get inputs
        education = request.form.get("education")
        primary_instrument = request.form.get("primary_instrument")
        secondary_instrument = request.form.get("secondary_instrument")
        
        # store inputs into table -> columns: user_id, education, primary_instrument, secondary_instrument
        db.execute("INSERT INTO personal_info (user_id,education,primary_instrument,secondary_instrument) VALUES (:id,:ed,:pi,:si)", id = session["user_id"], ed =  education, pi = primary_instrument, si = secondary_instrument)
        
        return redirect(url_for("upload"))


@app.route("/editpersonalinfo", methods=["GET","POST"])
@login_required
def editpersonalinfo():
    
    # if method is GET, display personal info page, otherwise store data
    if request.method == "GET":
        return render_template("editpersonalInfo.html")
    elif request.method =="POST":
        
        # get inputs
        education = request.form.get("education")
        primary_instrument = request.form.get("primary_instrument")
        secondary_instrument = request.form.get("secondary_instrument")
        
        # store inputs into table -> columns: user_id, education, primary_instrument, secondary_instrument
        db.execute("UPDATE personal_info SET education = :education WHERE user_id = :user_id", education = education, user_id = session["user_id"])
        db.execute("UPDATE personal_info SET primary_instrument = :primary_instrument WHERE user_id = :user_id", primary_instrument = primary_instrument, user_id = session["user_id"])
        db.execute("UPDATE personal_info SET secondary_instrument = :secondary_instrument WHERE user_id = :user_id", secondary_instrument = secondary_instrument, user_id = session["user_id"])
        
        return redirect(url_for("index"))


@app.route("/upload", methods=["GET","POST"])
@login_required
def upload():
    
    # if method is GET, display upload  page, otherwise store files
    if request.method == "GET":
        return render_template("upload.html")
    elif request.method == "POST" and "photo" in request.files:
        
        # create custom filename
        id = session["user_id"]
        pic_name = "user" + str(id) + "."
        
        # save file uploaded
        filename = photos.save(request.files["photo"], name=pic_name)
        
        # insert filename into database
        db.execute("UPDATE personal_info SET profile_picture = :filename WHERE user_id = :id", id = session["user_id"], filename = filename)
        
        return redirect(url_for("index"))
    
    # if no file was submitted    
    return apology("An error occurred")
    
@app.route("/editupload", methods=["GET","POST"])
@login_required
def editupload():
    
    # if method is GET, display upload  page, otherwise store files
    if request.method == "GET":
        return render_template("editUpload.html")
    elif request.method == "POST" and "photo" in request.files:
        
        # create custom filename
        id = session["user_id"]
        pic_name = "user" + str(id) + "."

        # delete existing picture if it already exists
        personal_info = db.execute("SELECT * FROM personal_info WHERE user_id = :user_id", user_id = session["user_id"])
        file_name = personal_info[0]["profile_picture"]
        filepath = os.getcwd() + "/static/uploads/img/" + file_name
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # save file uploaded
        filename = photos.save(request.files["photo"], name=pic_name)
        
        # insert filename into database
        db.execute("UPDATE personal_info SET profile_picture = :filename WHERE user_id = :id", id = session["user_id"], filename = filename)
        
        return redirect(url_for("index"))
    
    # if no file was submitted    
    return apology("An error occurred")


@app.route("/")
@login_required
def index():
    
    # get information from users table and personal_info table
    user = db.execute("SELECT * FROM users JOIN personal_info ON users.id = personal_info.user_id WHERE user_id = :user_id", user_id = session["user_id"])
    
    if len(user) < 1:
        return redirect(url_for("personalinfo"))
    
    first_name = str.capitalize(user[0]["first_name"])
    last_name = str.capitalize(user[0]["last_name"])
    full_name = first_name + " " + last_name
    
    education = user[0]["education"]
    primary_instrument = str.capitalize(user[0]["primary_instrument"])
    secondary_instrument = str.capitalize(user[0]["secondary_instrument"])
    
    
    pic_name = user[0]["profile_picture"]
    
    if pic_name == None:
        return redirect(url_for("upload"))
        
    profile_picture = "/static/uploads/img/" + pic_name
    
    return render_template("index.html", full_name = full_name, education = education, primary_instrument = primary_instrument, secondary_instrument = secondary_instrument, profile_picture = profile_picture)


@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))
    
@app.route("/createbiography", methods=["GET","POST"])
@login_required
def createbiography():
    if request.method == "GET":
        
        # display edit form
        bio_check = db.execute("SELECT * FROM biography WHERE user_id = :user_id", user_id = session["user_id"])
        
        if not bio_check:
            return render_template("editBio.html", value = "")
        else:
            value = bio_check[0]["bio"]
            return render_template("editBio.html", value = value)
    
    elif request.method == "POST":
        
        # check and get inputs from form
        if not request.form.get("biography"):
            return apology("No text was entered")
        
        biography = request.form.get("biography")
        
        # see if biography exists
        bio_check = db.execute("SELECT * FROM biography WHERE user_id = :user_id", user_id = session["user_id"])
        
        if not bio_check:
            db.execute("INSERT INTO biography (user_id,bio,last_updated) VALUES (:user_id,:biography,CURRENT_TIMESTAMP)", user_id = session["user_id"], biography=biography)
        else:
            db.execute("UPDATE biography SET bio = :bio, last_updated = CURRENT_TIMESTAMP WHERE user_id = :user_id", bio = biography, user_id = session["user_id"])
            
        # display bio webpage
        return redirect(url_for("biography"))


@app.route("/biography", methods=["GET","POST"])
@login_required
def biography():
    """Displays user's biography."""
    
     # look for user's bio
    user_bio = db.execute("SELECT * FROM biography WHERE user_id = :user_id", user_id=session["user_id"])
    
    # if it doesn't exist, redirect to create one
    if not user_bio:
        return redirect(url_for("createbiography"))
    
    # if it does exist, display it
    biography = user_bio[0]["bio"]
    return render_template("displayBio.html", biography=biography)


@app.route("/replist", methods=["GET","POST"])
@login_required
def replist():
    """Displays user's rep list."""
    
    # if user request is GET, display replist
    if request.method == "GET":
        
        # query database for all user's rep
        rep_list = db.execute("SELECT * FROM rep_list WHERE user_id = :user_id ORDER BY date_played ASC", user_id = session["user_id"])
        
        return render_template("replist.html", rep_list = rep_list)

    elif request.method == "POST":
        
        # check inputs
        if not request.form.get("piece"):
            return apology("Missing piece name")
        
        # store inputs
        piece = request.form.get("piece")
        composer = request.form.get("composer")
        instrument = request.form.get("instrument")
        date_played = request.form.get("date_played")
        ensemble = request.form.get("ensemble")
        notes = request.form.get("notes")
        
        # store in database
        db.execute("INSERT INTO rep_list (user_id,piece,composer,instrument,date_played,ensemble,notes) VALUES (:user_id,:piece,:composer,:instrument,:date_played,:ensemble,:notes)", 
        user_id=session["user_id"], piece=piece, composer=composer, instrument=instrument, date_played=date_played, ensemble=ensemble, notes=notes)
        
        return redirect(url_for("replist"))