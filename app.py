import datetime
import functools
import os
import re
import urllib
import uuid

from flask import (Flask, abort, flash, Markup, redirect, render_template, request, Response, session, url_for)
from markdown import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.extra import ExtraExtension
from micawber import bootstrap_basic, parse_html
from micawber.cache import Cache as OEmbedCache
from peewee import *
from playhouse.flask_utils import FlaskDB, get_object_or_404, object_list
from playhouse.sqlite_ext import *

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'secret'
APP_DIR = os.path.dirname(os.path.realpath(__file__))
DATABASE = 'sqliteext:///%s' % os.path.join(APP_DIR, 'blog.db')
DEBUG = False
SECRET_KEY = 'shhh, secret'
SITE_WIDTH = 800


app = Flask(__name__)
app.config.from_object(__name__)

flask_db = FlaskDB(app)
database = flask_db.database

oembed_providers = bootstrap_basic(OEmbedCache())

class my_dictionary(dict):  
  
    # __init__ function  
    def __init__(self):  
        self = dict()  
          
    # Function to add key:value  
    def add(self, key, value):  
        self[key] = value 

    def containsKey(self, key):
        for k, v in self.items():
            if k == key:
                return True
        return False

    def containsValue(self, value):
        for k, v in self.items():
            if v == value:
                return True
        return False
        

session_map = my_dictionary()

class Role(flask_db.Model):
    name = CharField(unique=True, primary_key=True)

class User(flask_db.Model):
    #active = BooleanField()

    #email = CharField(unique=True)
    #email_confirmed_at = DateTimeField(default=datetime.datetime.now, index=True)
    password = CharField()

    user_name = CharField(unique=True)

    roles = ForeignKeyField(Role, backref='users')

class Entry(flask_db.Model):
    title = CharField()
    slug = CharField(unique=True)
    content = TextField()
    published = BooleanField(index=True)
    timestamp = DateTimeField(default=datetime.datetime.now, index=True)
    author = ForeignKeyField(User, backref='entries')

    @property
    def html_content(self):
        hilite = CodeHiliteExtension(linenums=False, css_class='highlight')
        extras = ExtraExtension()
        markdown_content = markdown(self.content, extentions=[hilite, extras])
        oembed_content = parse_html(markdown_content, oembed_providers, urlize_all=True, maxwidth=app.config['SITE_WIDTH'])
        return Markup(oembed_content)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = re.sub('[^\w]+', '-', self.title.lower()).strip('-')
        ret = super(Entry, self).save(*args, **kwargs)

        self.update_search_index()
        return ret

    def update_search_index(self):
        exists = (FTSEntry
                  .select(FTSEntry.docid)
                  .where(FTSEntry.docid == self.id)
                  .exists())
        content = '\n'.join((self.title, self.content))
        if exists:
            (FTSEntry
             .update({FTSEntry.content: content})
             .where(FTSEntry.docid == self.id)
             .execute())
        else:
            FTSEntry.insert({FTSEntry.docid: self.id, FTSEntry.content: content}).execute()

    @classmethod
    def public(cls):
        return Entry.select().where(Entry.published == True)

    @classmethod
    def drafts(cls):
        return Entry.select().where(Entry.published == False)

    @classmethod
    def search(cls, query):
        words = [word.strip() for word in query.split() if word.strip()]
        if not words:
            return Entry.select().where(Entry.id == 0)
        else:
            search = ' '.join(words)

        return (Entry.select(Entry, FTSEntry.rank().alias('score')).join(FTSEntry, on=(Entry.id == FTSEntry.docid)).where((Entry.published == True) & (FTSEntry.match(search))).order_by(SQL('score')))




# TODO make own system of seeing users permissions, as not using flask setup


class FTSEntry(FTSModel):
    content = SearchField()

    class Meta:
        database = database



def login_required(fn):
    @functools.wraps(fn)
    def inner(*args, **kwargs):
        if session.get('logged_in'):
            if session_map.containsKey(session.get('unique')):
                return fn(*args, **kwargs)
            else:
                session.clear()
        return redirect(url_for('login', next=request.path))
    return inner

@app.route('/create_user/', methods=['GET', 'POST'])
def create_user():
    next_url = request.args.get('next') or request.form.get('next')
    if request.method == 'POST' and request.form.get('username') and request.form.get('password'):
        username = request.form.get('username')
        password = request.form.get('password')
        for user in User.select():
            if user.user_name == username:
                flash('A user with that name already exists!', 'danger')
                return render_template('create_user.html', next_url=next_url)
        if not username == '' and not password == '':
            user = User(user_name=username, password=password)
            user.roles = Role(name='User')
            user.save()
            
            flash('User created!', 'success')
            return render_template('login.html', next_url=next_url)
        else:
            flash('You must enter a username and a password', 'danger')
    return render_template('create_user.html', next_url=next_url)

@app.route('/login/', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next') or request.form.get('next')
    if request.method == 'POST' and request.form.get('password') and request.form.get('username'):
        username = request.form.get('username')
        password = request.form.get('password')
        if password == app.config['ADMIN_PASSWORD'] and username == app.config['ADMIN_USERNAME']:
            session['logged_in'] = True
            session['unique'] = uuid.uuid1()
            session.permanent = True
            flash('You are now logged in.', 'success')
            return redirect(next_url or url_for('index'))
        else:
            for user in User.select():
                if user.user_name == username and user.password == password:
                    session['logged_in'] = True
                    session['unique'] = uuid.uuid1()
                    session.permanent = True
                    session_map.add(session.get('unique'), user)
                    flash('You are now logged in.', 'success')
                    return redirect(next_url or url_for('index'))
            flash('Incorrect login details!', 'danger')
    return render_template('login.html', next_url=next_url)

@app.route('/logout/', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        try:
            session_map.pop(session.get('unique'))
            session.clear()
        except KeyError:
            session.clear()
        return redirect(url_for('login'))
    return render_template('logout.html')


@app.route('/')
def index():
    if session.get('logged_in'):
        if not session_map.containsKey(session.get('unique')):
            session.clear()
    search_query = request.args.get('q')
    if search_query:
        query = Entry.search(search_query)
    else:
        query = Entry.public().order_by(Entry.timestamp.desc())
    return object_list('index.html', query, search=search_query, check_bounds=False)


# init login required view
@app.route('/drafts/')
@login_required
def drafts():
    query = Entry.drafts().order_by(Entry.timestamp.desc())
    return object_list('index.html', query)

# Create view
@app.route('/create/', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        if request.form.get('title') and request.form.get('content'):
            entry = Entry.create(title=request.form['title'], content=request.form['content'], published=request.form.get('published') or False)
            flash('Entry created successfully!', 'success')
            if entry.published:
                return redirect(url_for('detail', slug=entry.slug))
            else:
                return redirect(url_for('edit', slug=entry.slug))
        else:
            flash('Title and Content are required!', 'danger')
    
    return render_template('create.html', entry=Entry(title='', content=''))


# Detail view 
@app.route('/<slug>/')
def detail(slug):
    if session.get('logged_in'):
        query = Entry.select()
    else:
        query = Entry.public()
    entry = get_object_or_404(query, Entry.slug == slug)
    return render_template('detail.html', entry=entry)


# Edit view
@app.route('/<slug>/edit/', methods=['GET', 'POST'])
@login_required
def edit(slug):
    entry = get_object_or_404(Entry, Entry.slug == slug)
    if request.method == 'POST':
        if request.form.get('title') and request.form.get('content'):
            entry.title = request.form['title']
            entry.content = request.form['content']
            entry.published = request.form.get('published') or False
            entry.save()

            flash('Entry saved successfully!', 'success')
            if entry.published:
                return redirect(url_for('detail', slug=entry.slug))
            else:
                return redirect(url_for('edit', slug=entry.slug))
        else:
            flash('Title and Content are required!', 'danger')
    return render_template('edit.html', entry=entry)

@app.template_filter('clean_querystring')
def clean_querystring(request_args, *keys_to_remove, **new_values):
    querystring = dict((key, value) for key, value in request_args.items())
    for key in keys_to_remove:
        querystring.pop(key, None)
    querystring.update(new_values)
    return urllib.parse.urlencode(querystring)

@app.errorhandler(404)
def not_found(exc):
    return Response('<h3>Not Found</h3>'), 404

def main():
    database.create_tables([Entry, FTSEntry, User, Role])
    Role.get_or_create(name='User')
    Role.get_or_create(name='Moderator')
    Role.get_or_create(name='Admin')
    app.run(debug=True)

if __name__ == "__main__":
    main()





