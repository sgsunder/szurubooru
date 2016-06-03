from sqlalchemy import Column, Integer, Unicode, DateTime
from sqlalchemy.orm import column_property
from sqlalchemy.sql.expression import func, select
from szurubooru.db.base import Base
from szurubooru.db.post import Post, PostScore, PostFavorite
from szurubooru.db.comment import Comment

class User(Base):
    __tablename__ = 'user'

    AVATAR_GRAVATAR = 'gravatar'
    AVATAR_MANUAL = 'manual'

    RANK_ANONYMOUS = 'anonymous'
    RANK_RESTRICTED = 'restricted'
    RANK_REGULAR = 'regular'
    RANK_POWER = 'power'
    RANK_MODERATOR = 'moderator'
    RANK_ADMINISTRATOR = 'administrator'
    RANK_NOBODY = 'nobody' # used for privileges: "nobody can be higher than admin"

    user_id = Column('id', Integer, primary_key=True)
    name = Column('name', Unicode(50), nullable=False, unique=True)
    password_hash = Column('password_hash', Unicode(64), nullable=False)
    password_salt = Column('password_salt', Unicode(32))
    email = Column('email', Unicode(64), nullable=True)
    rank = Column('rank', Unicode(32), nullable=False)
    creation_time = Column('creation_time', DateTime, nullable=False)
    last_login_time = Column('last_login_time', DateTime)
    avatar_style = Column(
        'avatar_style', Unicode(32), nullable=False, default=AVATAR_GRAVATAR)

    post_count = column_property(
        select([func.coalesce(func.count(1), 0)]) \
        .where(Post.user_id == user_id) \
        .correlate_except(Post))

    comment_count = column_property(
        select([func.coalesce(func.count(1), 0)]) \
        .where(Comment.user_id == user_id) \
        .correlate_except(Comment))

    favorite_post_count = column_property(
        select([func.coalesce(func.count(1), 0)]) \
        .where(PostFavorite.user_id == user_id) \
        .correlate_except(PostFavorite))

    liked_post_count = column_property(
        select([func.coalesce(func.count(1), 0)]) \
        .where(PostScore.user_id == user_id) \
        .where(PostScore.score == 1) \
        .correlate_except(PostScore))

    disliked_post_count = column_property(
        select([func.coalesce(func.count(1), 0)]) \
        .where(PostScore.user_id == user_id) \
        .where(PostScore.score == -1) \
        .correlate_except(PostScore))
