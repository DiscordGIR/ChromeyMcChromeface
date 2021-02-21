import mongoengine

class User(mongoengine.Document):
    _id                 = mongoengine.IntField(required=True)
    is_muted            = mongoengine.BooleanField(default=False, required=True)
    offline_report_ping = mongoengine.BooleanField(default=False, required=True)
    
    meta = {
        'db_alias': 'default',
        'collection': 'users'
    }