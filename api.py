from graphene import Field, Int, List, NonNull, ObjectType, String
from graphql.language.ast import FragmentSpread

from models import Follow, Like, Post, User


def get_ast_fields(ast, fragments):
    field_asts = ast.selection_set.selections
    for field_ast in field_asts:
        field_name = field_ast.name.value
        if isinstance(field_ast, FragmentSpread):
            for field in fragments[field_name].selection_set.selections:
                yield {
                    "field": field.name.value,
                    "children": get_ast_fields(field, fragments)
                    if hasattr(field, "selection_set") and field.selection_set
                    else [],
                }
            continue
        yield {
            "field": field_name,
            "children": get_ast_fields(field_ast, fragments)
            if field_ast.selection_set
            else [],
        }


def info_to_query(info):
    """
    Given a Graphene ResolveInfo object, returns a Peewee
    query to fetch the requested data
    """
    # info.return_type.graphene_type denotes the thing we are resolving
    #   (or if it is a list, info.return_type.of_type.graphene_type)
    # info.parent_type.graphene_type denotes the parent type we are resolving
    # info.field_asts contains the requested fields on the object we are resolving,
    #   and can be turned into something more intelligible with get_ast_fields


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
        return [like.post for like in source.likes]


class PostNode(ObjectType):
    class Meta:
        name = "Post"

    id = Int(required=True)
    author = Field(UserNode, required=True)
    content = String(required=True)
    liked_by = List(UserNode)

    def resolve_liked_by(source, info):
        return [like.user for like in Like.select().where(Like.post == source.id)]


class Query(ObjectType):
    users = List(UserNode, usernames=List(NonNull(String)))
    posts = List(PostNode)

    def resolve_users(source, info, usernames):
        import pdb

        pdb.set_trace()
        query = User.select()
        if usernames:
            query = query.where(User.username << usernames)
        return list(query)

    def resolve_posts(source, info):
        return list(Post.select())
