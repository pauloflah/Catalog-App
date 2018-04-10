from flask import Flask, render_template, url_for, request, redirect
from flask import jsonify, make_response, flash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, CategoryList, CategoryItem, User
from flask import session as login_session
import random
import string
import json
import httplib2
import requests
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
from functools import wraps

app = Flask(__name__)

engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())[
    'web']['client_id']
APPLICATION_NAME = "Catalog App"

# User Functions


def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# Flask Login Decorator


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in login_session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
@app.route('/catalog')
# Show all categories from the list
def showCategories():
    categoryList = session.query(CategoryList).all()
    categoryItems = session.query(CategoryItem).all()
    # return "This page will show all my categories"
    return render_template('categoryList.html', categoryList=categoryList,
                           categoryItems=categoryItems)


@app.route('/catalog/<int:catalog_id>')
@app.route('/catalog/<int:catalog_id>/items')
def showCategory(catalog_id):
    # Get all categories
    categories = session.query(CategoryList).all()

    # Get category
    category = session.query(CategoryList).filter_by(id=catalog_id).first()

    # Get name of category
    categoryName = category.name

    # Get all items of a specific category
    categoryItems = session.query(CategoryItem).filter_by(
        category_id=catalog_id).all()

    # Get count of category items
    categoryItemsCount = session.query(
        CategoryItem).filter_by(category_id=catalog_id).count()

    return render_template('category.html', categories=categories,
                           categoryItems=categoryItems,
                           categoryName=categoryName,
                           categoryItemsCount=categoryItemsCount)


@app.route('/catalog/<int:catalog_id>/items/<int:item_id>')
def showCategoryItem(catalog_id, item_id):
    categoryItem = session.query(CategoryItem).filter_by(id=item_id).first()
    ownerID = getUserInfo(categoryItem.user_id)

    return render_template('categoryItem.html', categoryItem=categoryItem,
                           ownerID=ownerID)


@app.route('/catalog/add', methods=['GET', 'POST'])
@login_required
def addCategoryItem():
    if request.method == 'POST':
        if not request.form['name']:
            flash('Please add an item name')
            return redirect(url_for('addCategoryItem'))
        if not request.form['description']:
            flash('Please add an item description')
            return redirect(url_for('addCategoryItem'))
        newCategoryItem = CategoryItem(name=request.form['name'],
                                       description=request.form['description'],
                                       category_id=request.form['category'],
                                       user_id=login_session['user_id'])
        session.add(newCategoryItem)
        session.commit()
        return redirect(url_for('showCategories'))
    else:
        categories = session.query(CategoryList).all()
        return render_template('addCategoryItem.html', categories=categories)


@app.route('/catalog/<int:catalog_id>/items/<int:item_id>/edit',
           methods=['GET', 'POST'])
@login_required
def editCategoryItem(catalog_id, item_id):
    categoryItem = session.query(CategoryItem).filter_by(id=item_id).first()
    owner = getUserInfo(categoryItem.user_id)
    if owner.id != login_session['user_id']:
        return redirect('/catalog')

    categories = session.query(CategoryList).all()

    if request.method == 'POST':
        if request.form['name']:
            categoryItem.name = request.form['name']
        if request.form['description']:
            categoryItem.description = request.form['description']
        if request.form['category']:
            categoryItem.category_id = request.form['category']
        return redirect(url_for('showCategoryItem',
                                catalog_id=categoryItem.category_id,
                                item_id=categoryItem.id))
    else:
        return render_template('editCategoryItem.html',
                               categoryList=categories,
                               categoryItem=categoryItem)


@app.route('/catalog/<int:catalog_id>/items/<int:item_id>/delete',
           methods=['GET', 'POST'])
@login_required
def deleteCategoryItem(catalog_id, item_id):
    categoryItem = session.query(CategoryItem).filter_by(id=item_id).first()
    owner = getUserInfo(categoryItem.user_id)

    if owner.id != login_session['user_id']:
        return redirect('/catalog')

    if request.method == 'POST':
        session.delete(categoryItem)
        session.commit()
        return redirect(url_for('showCategory',
                                catalog_id=categoryItem.category_id))
    else:
        return render_template('deleteCategoryItem.html',
                               categoryItem=categoryItem)

# Create anti-forgery state token


@app.route('/login')
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/logout')
def logout():
    if login_session['provider'] == 'facebook':
        fbdisconnect()
        del login_session['facebook_id']

    if login_session['provider'] == 'google':
        gdisconnect()
        del login_session['gplus_id']

    del login_session['user_id']
    del login_session['username']
    del login_session['email']
    del login_session['picture']
    del login_session['provider']
    del login_session['access_token']

    return redirect(url_for('showCategories'))


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    access_token = request.data
    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_secret']

    url = (
        'https://graph.facebook.com/oauth/access_token?' +
        'grant_type=fb_exchange_token&' +
        'client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
                              app_id, app_secret, access_token))
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    userinfo_url = "https://graph.facebook.com/v2.11/me"
    token = json.loads(result.split("&")[0])

    url = (
        'https://graph.facebook.com/v2.11/me?access_token=' +
        '%s&fields=name,id,email' % token["access_token"])
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    data = json.loads(result)

    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]
    login_session['access_token'] = token["access_token"]

    # Get user picture
    picurl = (
              'https://graph.facebook.com/%s'
              '/picture?redirect=0&height=200&width=200&access_token=%s' % (
                       login_session['facebook_id'], token["access_token"]))
    login_session['picture'] = url

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    return "Login Successful!"


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (
        facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "Logout Successful!"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
                                 'Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['provider'] = 'google'
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;'
    output += 'border-radius: 150px;-webkit-border-radius: 150px;'
    output += '-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps(
            'Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    url = (
           'https://accounts.google.com/o/oauth2/revoke?token=%s'
           % login_session['access_token'])
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps(
            'Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/catalog/JSON')
def showCategoriesJSON():
    categoryList = session.query(CategoryList).all()
    return jsonify(categoryList=[categoryList.serialize for category
                                 in categoryList])


@app.route('/catalog/<int:catalog_id>/JSON')
@app.route('/catalog/<int:catalog_id>/items/JSON')
def showCategoryJSON(catalog_id):
    categoryItems = session.query(CategoryItem).filter_by(
        category_id=catalog_id).all()
    return jsonify(categoryItems=[categoryItem.serialize for categoryItem
                                  in categoryItems])


@app.route('/catalog/<int:catalog_id>/items/<int:item_id>/JSON')
def showCategoryItemJSON(catalog_id, item_id):
    categoryItem = session.query(CategoryItem).filter_by(id=item_id).first()
    return jsonify(categoryItem=[categoryItem.serialize])


if __name__ == '__main__':
    app.debug = True
    app.secret_key = 'super_secret_key'
    app.run(host='0.0.0.0', port=5000)
