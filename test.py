import pytest

from graphene import Schema
from peewee import SqliteDatabase

from api import Query
from models import User, Post, Follow, Like, db


class CountingSqliteDatabase(SqliteDatabase):
    def __init__(self, database, pragmas=None, *args, **kwargs):
        self.queries_executed = 0
        super(CountingSqliteDatabase, self).__init__(
            database, pragmas=pragmas, *args, **kwargs
        )

    def execute_sql(self, sql, params=None, require_commit=True):
        self.queries_executed += 1
        return super(CountingSqliteDatabase, self).execute_sql(
            sql, params=params, require_commit=require_commit
        )


@pytest.fixture
def db_connection():
    memdb = CountingSqliteDatabase(":memory:")
    models = [User, Post, Follow, Like]
    db.initialize(memdb)
    db.connect()
    db.create_tables(models)
    yield memdb
    db.drop_tables(models)
    db.close()


def test_api(db_connection):
    u1 = User.create(username="user1")
    u2 = User.create(username="user2")
    u3 = User.create(username="user3")
    u4 = User.create(username="user4")
    u5 = User.create(username="user5")
    u6 = User.create(username="user6")
    u7 = User.create(username="user7")

    Follow.create(follower=u1, followee=u2)
    Follow.create(follower=u1, followee=u3)
    Follow.create(follower=u1, followee=u4)
    Follow.create(follower=u2, followee=u1)
    Follow.create(follower=u2, followee=u6)
    Follow.create(follower=u3, followee=u2)
    Follow.create(follower=u4, followee=u3)
    Follow.create(follower=u4, followee=u5)
    Follow.create(follower=u5, followee=u1)
    Follow.create(follower=u6, followee=u2)
    Follow.create(follower=u6, followee=u3)
    Follow.create(follower=u6, followee=u7)
    Follow.create(follower=u7, followee=u1)
    Follow.create(follower=u7, followee=u2)

    p1 = Post.create(author=u2, content="lorem ipsum")
    p2 = Post.create(author=u3, content="dolorum")
    p3 = Post.create(author=u6, content="foo bar")

    Like.create(user=u1, post=p1)
    Like.create(user=u1, post=p2)
    Like.create(user=u1, post=p3)

    schema = Schema(query=Query)
    query = """
    {
        users(usernames: ["user1"]) {
            username,
            following {
                username
                followers {
                    username
                }
            }
            likes {
                author {
                    username
                }
                content
            }
        }
    }
    """
    result = schema.execute(query)
    assert result.data == {
        u"users": [
            {
                u"following": [
                    {
                        u"followers": [
                            {u"username": u"user1"},
                            {u"username": u"user3"},
                            {u"username": u"user6"},
                            {u"username": u"user7"},
                        ],
                        u"username": u"user2",
                    },
                    {
                        u"followers": [
                            {u"username": u"user1"},
                            {u"username": u"user4"},
                            {u"username": u"user6"},
                        ],
                        u"username": u"user3",
                    },
                    {u"followers": [{u"username": u"user1"}], u"username": u"user4"},
                ],
                u"likes": [
                    {u"author": {u"username": u"user2"}, u"content": u"lorem ipsum"},
                    {u"author": {u"username": u"user3"}, u"content": u"dolorum"},
                    {u"author": {u"username": u"user6"}, u"content": u"foo bar"},
                ],
                u"username": u"user1",
            }
        ]
    }
    assert db_connection.queries_executed == 59
