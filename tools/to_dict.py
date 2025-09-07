async def to_dict(obj):
    return {c.key: getattr(obj, c.key) for c in obj.__table__.columns if c.key != 'groups' and c.key != 'id' and getattr(obj, c.key) is not None}