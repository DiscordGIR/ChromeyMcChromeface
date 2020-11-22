import mongoengine
import datetime

class Case(mongoengine.EmbeddedDocument):
    _id               = mongoengine.IntField(required=True)
    _type             = mongoengine.StringField(required=True)
    date              = mongoengine.DateField(default=datetime.datetime.now, required=True)
    until             = mongoengine.DateField(default=None)
    mod_id            = mongoengine.IntField(required=True)
    mod_tag           = mongoengine.StringField(required=True)
    reason            = mongoengine.StringField(required=True)
    punishment_points = mongoengine.IntField(default=0)
    lifted            = mongoengine.BooleanField(default=False)
    lifted_reason     = mongoengine.StringField()