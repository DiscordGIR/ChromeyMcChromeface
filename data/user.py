import mongoengine

class User(mongoengine.Document):
    _id                 = mongoengine.IntField(required=True)
    is_muted            = mongoengine.BooleanField(default=False, required=True)
    offline_report_ping = mongoengine.BooleanField(default=False, required=True)
    raid_verified       = mongoengine.BooleanField(default=False, required=True)
    
    karma                  = mongoengine.IntField(required=True, default=0)
    karma_received_history = mongoengine.ListField(default=[])
    karma_given_history    = mongoengine.ListField(default=[])
    
    meta = {
        'db_alias': 'default',
        'collection': 'users'
    }