from graphene import Field, Int, List, NonNull, ObjectType, String
from graphql.language.ast import FragmentSpread
from graphql.type.definition import GraphQLList

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


def field_asts_to_list(ast_gen):
    asts = []
    for ast in ast_gen:
        ast["children"] = field_asts_to_list(ast["children"])
        asts.append(ast)
    return asts


def get_peewee_type(graphene_type):
    # TODO make this smarter/more convenient
    if isinstance(graphene_type, GraphQLList):
        graphene_type = graphene_type.of_type
    return TYPE_MAPPING.get(graphene_type.graphene_type)


def prefetch_query(info):
    """
    Given a Graphene ResolveInfo object and an initial Peewee query,
    returns a new Peewee query with the correct JOINs to fetch all
    requested fields (even nested ones).
    """
    # info.return_type.graphene_type denotes the thing we are resolving
    #   (or if it is a list, info.return_type.of_type.graphene_type)
    # info.parent_type.graphene_type denotes the parent type we are resolving
    # info.field_asts contains the requested fields on the object we are resolving,
    #   and can be turned into something more intelligible with get_ast_fields
    peewee_type = get_peewee_type(info.return_type)
    if peewee_type:
        # TODO will there ever be more than one top-level field AST?
        field_ast = info.field_asts[0]
        args = field_ast.arguments

        base_query = (
            peewee_type.select()
            if isinstance(info.return_type, GraphQLList)
            else peewee_type.get()
        )

        return base_query


class UserNode(ObjectType):
    class Meta:
        name = "User"

    id = Int(required=True)
    username = String(required=True)
    followers = List("api.UserNode")
    following = List("api.UserNode")
    likes = List("api.PostNode")

    def resolve_followers(source, info):
        if source.follower_set:
            return [follow.follower for follow in source.follower_set]
        return [
            follow.follower
            for follow in Follow.select().where(Follow.followee == source.id)
        ]

    def resolve_following(source, info):
        if source.followee_set:
            return [follow.followee for follow in source.followee_set]
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
        # query = prefetch_query(info)
        # TODO this appraoch leads to lots of duplicated rows,
        # since we get many rows per top-level user due to
        # the joins. Find a way to properly aggregate the data
        # (maybe using subqueries instead of joins?)
        # https://docs.sqlalchemy.org/en/13/orm/loading_relationships.html#subquery-eager-loading
        FolloweeUser = User.alias()
        query = (
            User.select()
            # following
            .join(Follow, on=Follow.follower)
            .join(FolloweeUser, on=FolloweeUser.follower_set)
            # likes
            .switch(User)
            .join(Like)
            .join(Post)
        )
        if usernames:
            query = query.where(User.username << usernames)
        return list(query)

    def resolve_posts(source, info):
        return list(Post.select())


TYPE_MAPPING = {UserNode: User, PostNode: Post}
