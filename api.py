from graphene import Field, Int, List, NonNull, ObjectType, String

from models import Follow, Like, Post, User


class UserNode(ObjectType):
    class Meta:
        name = "User"

    id = Int(required=True)
    username = String(required=True)
    followers = List("api.UserNode")
    following = List("api.UserNode")
    likes = List("api.PostNode")

    def resolve_followers(source, info):
        return [
            follow.follower
            for follow in Follow.select().where(Follow.followee == source.id)
        ]

    def resolve_following(source, info):
        return [
            follow.followee
            for follow in Follow.select().where(Follow.follower == source.id)
        ]

    def resolve_likes(source, info):
        return [
            like.post
            for like in source.likes
        ]


class PostNode(ObjectType):
    class Meta:
        name = "Post"

    id = Int(required=True)
    author = Field(UserNode, required=True)
    content = String(required=True)
    liked_by = List(UserNode)

    def resolve_liked_by(source, info):
        return [
            like.user
            for like in Like.select().where(Like.post == source.id)
        ]


class Query(ObjectType):
    users = List(UserNode, usernames=List(NonNull(String)))
    posts = List(PostNode)

    def resolve_users(source, info, usernames):
        query = User.select()
        if usernames:
            query = query.where(User.username << usernames)
        return list(query)

    def resolve_posts(source, info):
        return list(Post.select())
