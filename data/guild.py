import mongoengine
from data.filterword import FilterWord
from data.tag import Tag

class Guild(mongoengine.Document):
    _id                       = mongoengine.IntField(required=True)
    case_id                   = mongoengine.IntField(min_value=1, required=True)
    reaction_role_mapping     = mongoengine.DictField()
    role_nerds                = mongoengine.IntField()
    role_moderator            = mongoengine.IntField()
    role_mute                 = mongoengine.IntField()
    role_birthday             = mongoengine.IntField()
    
    channel_botspam           = mongoengine.IntField()
    channel_private           = mongoengine.IntField()
    channel_reaction_roles    = mongoengine.IntField()
    channel_reports           = mongoengine.IntField()
    channel_deals           = mongoengine.IntField()

    emoji_logging_webhook     = mongoengine.IntField()
    filter_excluded_channels  = mongoengine.ListField(default=[])
    filter_excluded_guilds    = mongoengine.ListField(default=[253908290105376768])
    filter_words              = mongoengine.EmbeddedDocumentListField(FilterWord, default=[])
    logging_excluded_channels = mongoengine.ListField(default=[])
    tags                      = mongoengine.EmbeddedDocumentListField(Tag, default=[])

    meta = {
        'db_alias': 'default',
        'collection': 'guilds'
    }

