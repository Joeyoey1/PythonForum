import datetime
from peewee import *
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from playhouse.sqlite_ext import SqliteExtDatabase, FTSModel, SearchField

# Initialize without a database initially, bind later
db = SqliteExtDatabase(None)

class BaseModel(Model):
    class Meta:
        database = db

class Role(BaseModel):
    name = CharField(unique=True, primary_key=True)

class User(UserMixin, BaseModel):
    user_name = CharField(unique=True)
    password_hash = CharField()
    role = ForeignKeyField(Role, backref='users', null=True) # Allow null for now or fix creation logic

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.user_name)

class UserFollow(BaseModel):
    user = ForeignKeyField(User, backref='followed')
    follower = ForeignKeyField(User, backref='follower')

class Entry(BaseModel):
    title = CharField()
    slug = CharField(unique=True)
    content = TextField()
    published = BooleanField(index=True, default=False)
    timestamp = DateTimeField(default=datetime.datetime.now, index=True)
    author = ForeignKeyField(User, backref='entries')

class FTSEntry(FTSModel):
    content = SearchField()
    class Meta:
        database = db

class Reply(BaseModel):
    content = TextField()
    timestamp = DateTimeField(default=datetime.datetime.now, index=True)
    author = ForeignKeyField(User, backref='replies')
    entry = ForeignKeyField(Entry, backref='replies')
