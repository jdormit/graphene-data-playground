from peewee import (
    CharField,
    Proxy,
    ForeignKeyField,
    Model,
    OperationalError,
    PrimaryKeyField,
    SqliteDatabase,
    TextField
)

db = Proxy()
database = SqliteDatabase("graphene-data-playground.db")
db.initialize(database)


class DataPlaygroundModel(Model):
    class Meta:
        database = db


class User(DataPlaygroundModel):
    id = PrimaryKeyField()
    username = CharField()


class Follow(DataPlaygroundModel):
    follower = ForeignKeyField(User, related_name="follower_set")
    followee = ForeignKeyField(User, related_name="followee_set")


class Post(DataPlaygroundModel):
    id = PrimaryKeyField()
    author = ForeignKeyField(User, related_name="posts")
    content = TextField()


class Like(DataPlaygroundModel):
    user = ForeignKeyField(User, related_name="likes")
    post = ForeignKeyField(Post, related_name="likes")
