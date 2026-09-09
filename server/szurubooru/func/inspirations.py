from datetime import datetime, timedelta, timezone

from szurubooru import config, db, errors, model


class InspirationCooldownError(errors.ValidationError):
    pass


def _get_cooldown_seconds() -> int:
    return int(config.config["inspirations"]["cooldown_seconds"])


def add_inspiration(post: model.Post, user: model.User) -> None:
    assert post
    assert user
    if not user.user_id:
        raise errors.AuthError("Must be logged in to do this.")
    last_time = user.last_inspiration_time
    if last_time is not None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cooldown = timedelta(seconds=_get_cooldown_seconds())
        if now - last_time < cooldown:
            raise InspirationCooldownError(
                "You must wait before inspiring another post."
            )
    inspiration = model.PostInspiration()
    inspiration.post = post
    inspiration.user = user
    inspiration.time = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.add(inspiration)


def reset_inspirations(post: model.Post) -> None:
    assert post
    db.session.query(model.PostInspiration).filter(
        model.PostInspiration.post_id == post.post_id
    ).delete()
