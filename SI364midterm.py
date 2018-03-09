
###############################
####### SETUP (OVERALL) #######
###############################

#-*- coding: utf-8 -*-
import sys
import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)

## Import statements
import json
import requests
import app_key_id

# Import statements
import os
from flask import Flask, render_template, session, redirect, url_for, flash, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, ValidationError, RadioField # Note that you may need to import more here! Check out examples that do what you want to figure out what.
from wtforms.validators import Required # Here, too
from flask_sqlalchemy import SQLAlchemy
from flask_script import Manager, Shell

## App setup code
app = Flask(__name__)
app.debug = True
app.use_reloader = True

## All app.config values
app.config['SECRET_KEY'] = 'hard to guess string'
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://localhost:5432/shdoong364midterm" 
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


## Statements for db setup (and manager setup if using Manager)
db = SQLAlchemy(app)
manager = Manager(app)

######################################
######## HELPER FXNS (If any) ########
######################################
API_KEY = app_key_id.API_KEY
APP_ID = app_key_id.APP_ID

def getInfo(q, ct, ing1, ing2, ing3):
    BASE_URL = 'http://api.yummly.com/v1/api/recipes?'
    if ct == 0:
        response = requests.get(BASE_URL, params={'_app_id': APP_ID, '_app_key': API_KEY, 'q':q, 'maxResult':1})
    if ct == 1:
        response = requests.get(BASE_URL, params={'_app_id': APP_ID, '_app_key': API_KEY, 'q':q, 'maxResult':1, 'allowedIngredient[]':ing1})
    if ct == 2:
        response = requests.get(BASE_URL, params={'_app_id': APP_ID, '_app_key': API_KEY, 'q':q, 'maxResult':1, 'allowedIngredient[]':ing1, 'allowedIngredient[]':ing2})
    if ct == 3:
        response = requests.get(BASE_URL, params={'_app_id': APP_ID, '_app_key': API_KEY, 'q':q, 'maxResult':1, 'allowedIngredient[]':ing1, 'allowedIngredient[]':ing2, 'allowedIngredient[]':ing3})                
    r_text = json.loads(response.text)['matches']
    return r_text

def getRecipeName(q, ct, ing1, ing2, ing3):
    data = getInfo(q, ct, ing1, ing2, ing3)
    return(''.join([x['recipeName'] for x in data]))

def getID(q, ct, ing1, ing2, ing3):
    data = getInfo(q, ct, ing1, ing2, ing3)
    for x in data:
        id1= x['id']
    return(id1)

def getRecipeInfo(q, ct, ing1, ing2, ing3):
    id2 = getID(q, ct, ing1, ing2, ing3)
    link = 'http://api.yummly.com/v1/api/recipe/'+id2+'?_app_id='+APP_ID+'&_app_key='+API_KEY
    response = requests.get(link)
    r_text = json.loads(response.text)
    return r_text

def getLink(q, ct, ing1, ing2, ing3):
    r_text = getRecipeInfo(q, ct, ing1, ing2, ing3)
    return r_text['attribution']['url']

def getIngredients(q, ct, ing1, ing2, ing3):
    data = getRecipeInfo(q, ct, ing1, ing2, ing3)
    return data['ingredientLines']

def getNutrition(q, ct, ing1, ing2, ing3):
    data = getRecipeInfo(q, ct, ing1, ing2, ing3)
    nutrition = ['FAT', 'ENERC_KCAL', 'CHOLE', 'NA', 'SUGAR', 'PROCNT', 'CA', 'CHOCDF']
    return ([(x['attribute'], (str(x['value']) + ' ' + x['unit']['plural'])) for x in data['nutritionEstimates'] if x['attribute'] in nutrition])

def getAttributes(q, ct, ing1, ing2, ing3):
    data = getRecipeInfo(q, ct, ing1, ing2, ing3)
    return (data['totalTime'], data['numberOfServings'], data['rating'])

def get_or_create_user(user): ##Allows a user to submit duplicate name to a form, but will not save duplicate name
    user1 = Names.query.filter_by(name=user).first()
    if user1:
        return user1
    else:
        user1 = Names(name=user)
        db.session.add(user1)
        db.session.commit()
        return user1

def get_or_create_recipe(q, user, ct, ing1, ing2, ing3):
    name = getRecipeName(q, ct, ing1, ing2, ing3)
    ingredients = getIngredients(q = name, ct = ct, ing1 = ing1, ing2 = ing2, ing3 = ing3)
    recipe = Recipe.query.filter_by(label = name, name_id = user.id).first() #Checks to see if that user already found that recipe
    recipe_gen = Recipe.query.filter_by(label = name).first() #Checks to see if the recipe was already found by another user
    url = getLink(q, ct, ing1, ing2, ing3)
    if recipe:
        return recipe
    ##If another user had already found the same recipe, add to the OtherFoundR database and make a note that it is in that database for later use
    elif recipe_gen:
        o = OtherFoundR.query.filter_by(recipe = name).first()
        if not o:
            others = OtherFoundR(recipe = recipe_gen.label, original_user = recipe_gen.name_id, new_user = user.id, recipe_id = recipe_gen.id, url = url)
            db.session.add(others)
            db.session.commit()
        return [recipe_gen, "yes"]
    #If recipe not found entirely, add it to the Recipe database
    elif not recipe and not recipe_gen:
        recipe = Recipe(label = name, ingredients = ingredients, url = url, name_id = user.id)
        db.session.add(recipe)
        db.session.commit()
        return recipe

def add_nutrition(q, user, ct, ing1, ing2, ing3):
    recip_id = get_or_create_recipe(q, user, ct, ing1, ing2, ing3)
    if type(recip_id) == list:
        recip_id = recip_id[0]
    checker = Nutrition.query.filter_by(recipe_id = recip_id.id).first()

    if not checker:
        nutrition_info = getNutrition(q, ct, ing1, ing2, ing3)
        nutrition = ['FAT', 'ENERC_KCAL', 'CHOLE', 'NA', 'SUGAR', 'PROCNT', 'CA', 'CHOCDF']
        d = {}
        for x in nutrition:
            d[x] = 0

        for x in nutrition_info:
            if x[0] in d:
                d[x[0]] = x[1]
        checker = Nutrition(calories = d['ENERC_KCAL'], sugar = d['SUGAR'], protein = d['PROCNT'], carbs = d['CHOCDF'], cholesterol = d['CHOLE'], calcium = d['CA'], sodium  = d['NA'], fat = d['FAT'], recipe_id = recip_id.id)
        db.session.add(checker)
        db.session.commit()
    return checker

def add_attributes(q, user, ct, ing1, ing2, ing3):
    recip_id = get_or_create_recipe(q, user, ct, ing1, ing2, ing3)
    if type(recip_id) == list:
        recip_id = recip_id[0]
    checker = Information.query.filter_by(recipe_id = recip_id.id).first()

    if not checker:
        att_info = getAttributes(q, ct, ing1, ing2, ing3)
        checker = Information(serving = att_info[1], tottime = att_info[0], rating = att_info[2], recipe_id = recip_id.id)
        db.session.add(checker)
        db.session.commit()
    return checker
##################
##### MODELS #####
##################

##Names and Recipe have a one-to-many relationship
class Names(db.Model):
    __tablename__ = "Names"
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(64))
    recipes = db.relationship('Recipe', backref = 'Names')

    def __repr__(self):
        return "{}, (ID: {})".format(self.name, self.id)

class Recipe(db.Model):
    __tablename__ = "Recipe"
    id = db.Column(db.Integer, primary_key = True)
    label = db.Column(db.String(128))
    ingredients = db.Column(db.String())
    url = db.Column(db.String())
    name_id = db.Column(db.Integer, db.ForeignKey('Names.id'))

    def __repr__(self):
        return "{}, {}, {}, ID:({})".format(self.label, self.ingredients, self.url, self.name_id)

class Information(db.Model):
    __tablename__ = "Information"
    id = db.Column(db.Integer, primary_key = True)
    serving = db.Column(db.Integer())
    tottime = db.Column(db.String())
    rating = db.Column(db.Float())
    recipe_id = db.Column(db.Integer, db.ForeignKey('Recipe.id'))

class Nutrition(db.Model):
    __tablename__ = "Nutrition"
    id = db.Column(db.Integer, primary_key = True)
    cholesterol = db.Column(db.String())
    calories = db.Column(db.String())
    sodium = db.Column(db.String())
    sugar = db.Column(db.String())
    protein = db.Column(db.String())
    calcium = db.Column(db.String())
    carbs = db.Column(db.String())
    fat = db.Column(db.String())
    recipe_id = db.Column(db.Integer, db.ForeignKey('Recipe.id'))

    def __repr__(self):
        return "{}, {}, {}, {}, {}, {}, {}, {}, ID:({})".format(self.cholesterol, self.calcium, self.sodium, self.sugar, self.protein, self.calcium, self.carbs, self.fat, self.recipe_id)

class OtherFoundR(db.Model):
    __tablename__ = "OtherFoundR"
    id = db.Column(db.Integer, primary_key = True)
    recipe = db.Column(db.String())
    original_user = db.Column(db.Integer)
    new_user = db.Column(db.Integer)
    recipe_id = db.Column(db.Integer)
    url = db.Column(db.String())

    def __repr__(self):
        return "{}, {}, {}, {}".format(self.id, self.recipe, self.name_id, self.recipe_id)
###################
###### FORMS ######
###################

class NameForm(FlaskForm):
    name = StringField("Please enter your name.",validators=[Required()])
    submit = SubmitField()

class Form(FlaskForm):
    name = StringField("Please enter your first and last name: ", validators=[Required("Name is required!")])

    def validate_name(self, field):
        if len(field.data.split()) < 2:
            raise ValidationError('Please enter your first AND last name separated with a space!')

    r = StringField("What would you like to find a recipe for? ", validators = [Required("Please input what you would like to search for!")])

    ing1 = StringField("Ingredient 1: ", validators = [])
    ing2 = StringField("Ingredient 2: ", validators = [])
    ing3 = StringField("Ingredient 3: ", validators = [])

    def validate_ing2(self, field):
        if len(field.data) > 0:
            if len(self.ing1.data) == 0:
                raise ValidationError('Please enter the first ingredient in the Ingredient 1 field!')

    def validate_ing3(self, field):
        if len(field.data) > 0:
            if len(self.ing2.data) == 0:
                raise ValidationError('Please enter your ingredients in the first or second ingredient field first!')
            else:
                if len(self.ing1.data) == 0:
                    raise ValidationError('Please enter your ingredients in the first or second ingredient field first!')
    submit = SubmitField()

class Nutrition_Form(FlaskForm):
    measures = RadioField("Which measure do you want to check? ", choices = [('cholesterol', 'cholesterol'), ('calories', 'calories'), ('sodium', 'sodium'), ('sugar', 'sugar'), ('protein', 'protein'), ('calcium', 'calcium'), ('carbs', 'carbs'), ('fat', 'fat')])
    hl = RadioField("Do you want the recipe with the highest or the lowest? ", choices = [('highest', 'highest'), ('lowest', 'lowest')])
    submit = SubmitField()

class Specific_User(FlaskForm):
    user = StringField("Which user's recipes do you want to view? ", validators = [Required("Please enter the user's name.")])
    submit = SubmitField()

    def validate_user(self, field):
        name_id = Names.query.filter_by(name = field.data).first()
        if not name_id:
            raise ValidationError("User does not exist, try again!")
#######################
###### VIEW FXNS ######
#######################
## Error handling routes - PROVIDED
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

##WTForm in home sends data to same page with POST to add data into databases
##Data from form is also sent to the redirected page
@app.route('/', methods=['POST', 'GET'])
def home():
    form = Form()
    if form.validate_on_submit():
        name = form.name.data
        recip = form.r.data
        ing1 = form.ing1.data
        ing2 = form.ing2.data
        ing3 = form.ing3.data
        ct = 0
        if len(ing1) != 0:
            ct += 1
        else:
            ing1 = "None"
        if len(ing2) != 0:
            ct += 1
        else:
            ing2 = "None"
        if len(ing3) != 0:
            ct += 1
        else:
            ing3 = "None"
        test = getInfo(q = recip, ct = ct, ing1 = ing1, ing2 = ing2, ing3 = ing3)
        if len(test) == 0:
            return render_template("not_found.html")
        user = get_or_create_user(user = name)
        getcreate = get_or_create_recipe(q = recip, user = user, ct = ct, ing1 = ing1, ing2 = ing2, ing3 = ing3)
        if type(getcreate) == list:
            other = getcreate[1]
        else:
            other = "no"
        add_nutrition(q = recip, user = user,  ct = ct, ing1 = ing1, ing2 = ing2, ing3 = ing3)
        add_attributes(q = recip, user = user,  ct = ct, ing1 = ing1, ing2 = ing2, ing3 = ing3)
        ##Requirement: use of redirect and url_for
        return redirect(url_for('your_recipe', name = name, ing1 = ing1, ing2 = ing2, ing3 = ing3, q = recip, other = other))
    flash(form.errors)
    return render_template('index.html', form=form)

@app.route('/names')
def all_names():
    names = Names.query.all()
    return render_template('name_example.html',names=names)

@app.route('/your_recipe/<string:name>/<string:ing1>/<string:ing2>/<string:ing3>/<string:q>/<string:other>')
def your_recipe(name, ing1, ing2, ing3, q, other):
    name_id = Names.query.filter_by(name = name).first().id
    recipes = [(x.label, x.url) for x in Recipe.query.filter_by(name_id = name_id).all()]
    recipes2 = [(Names.query.filter_by(id = x.original_user).first().name, x.url, x.recipe) for x in OtherFoundR.query.filter_by(new_user = name_id).all()]
    if other == "no":
        other = "None"
    else:
        other = "Yes"
    return render_template('your_recipe.html', name = name, recipes = recipes, ing1 = ing1, ing2 = ing2, ing3 = ing3, q = q, other = other, recipes_other = recipes2)

@app.route('/recipes')
def all_recipes():
    recipes = Recipe.query.all()
    info = [(r.label, r.ingredients, r.url) for r in recipes]
    return render_template('all_recipes.html', info = info)

##Uses post to send to same page
@app.route('/specific_user', methods = ["GET", "POST"])
def specific_user():
    form = Specific_User(request.form)
    if form.validate_on_submit():
        user = form.user.data
        name_id = Names.query.filter_by(name = user).first().id
        recipes = [(x.label, x.url) for x in Recipe.query.filter_by(name_id = name_id).all()]
        recipes2 = [(Names.query.filter_by(id = x.original_user).first().name, x.url, x.recipe) for x in OtherFoundR.query.filter_by(new_user = name_id).all()]
        return render_template('specific_user_info.html', name = user, recipes = recipes, recipes2 = recipes2)
    flash(form.errors)
    return render_template('specific_user_form.html', form=form)

##Nutrition form and recipe sends data to new page with GET
@app.route('/nutrition_form', methods = ["GET", "POST"])
def nutrition_checker():
    form = Nutrition_Form()
    return render_template('nutrition_checker.html', form = form)

@app.route('/nutrition_recipe', methods = ["GET", "POST"])
def HL_nutrition():
    if request.args:
        measure = request.args.get('measures')
        hl = request.args.get('hl')
        n_all = Nutrition.query.all()
        n = [{'cholesterol':nu.cholesterol, 'calories':nu.calories, 'sodium':nu.sodium, 'sugar':nu.sugar, 'protein':nu.protein, 'calcium':nu.calcium, 'carbs':nu.carbs, 'fat':nu.fat, 'id':nu.recipe_id} for nu in n_all]
        lst = []
        for d in n:
            for item in d:
                if item == measure:
                    lst.append((float(d[item].split()[0]), d['id']))
        sorted_lst = sorted(lst, key = lambda x:x[0])
        if hl == "highest":
            r = sorted_lst[-1]
        if hl == "lowest":
            r = sorted_lst[0]
        hl_recipe = Recipe.query.filter_by(id = r[1]).first().label
        url = Recipe.query.filter_by(id = r[1]).first().url
        return render_template('nutrition_recipe.html', hl = hl, measure = measure, n = hl_recipe, url = url)
    return redirect(url_for('nutrition_checker'))

@app.route('/most_servings')
def most_servings():
    info = Information.query.all()
    serving = [(x.serving, x.tottime, x.recipe_id, x.rating) for x in info]
    sorted_lst = sorted(serving, key = lambda y:y[0], reverse = True)
    serv = sorted_lst[0][0]
    tottime = sorted_lst[0][1]
    rating = sorted_lst[0][3]
    recipe = Recipe.query.filter_by(id = sorted_lst[0][2]).first().label
    url = Recipe.query.filter_by(id = sorted_lst[0][2]).first().url
    return render_template('most_servings.html', serv = serv, tottime = tottime, recip = recipe, url = url, rating = rating)

@app.route('/highest_rating')
def highest_rating():
    info = Information.query.all()
    serving = [(x.serving, x.tottime, x.recipe_id, x.rating) for x in info if x.rating == 5.0]
    ids = [z.recipe_id for z in info if z.rating == 5.0]
    sorted_lst = serving
    recipe = []
    for y in ids:
        recipe.append((Recipe.query.filter_by(id = y).first().label,Recipe.query.filter_by(id = y).first().url, Recipe.query.filter_by(id = y).first().id))
    return render_template('highest_rating.html', r = sorted_lst, recipe = recipe)

## Code to run the application...
if __name__ == '__main__':
    db.create_all() 
    app.run(use_reloader=True,debug=True)
# Put the code to do so here!
# NOTE: Make sure you include the code you need to initialize the database structure when you run the application!
