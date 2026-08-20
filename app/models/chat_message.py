from tortoise import fields, Model



class ChatMessage(Model):
    id = fields.IntField(pk=True)                                           # 整数主键
    user = fields.ForeignKeyField("models.User", related_name="chat_messages")           # 外键，指向 User
    message = fields.CharField(max_length=1000)                         # 用户发的内容
    reply = fields.CharField(max_length=10000)                           # AI 的回复
    created_at = fields.DatetimeField(auto_now_add=True)                         # 时间，自动填
    prompt_tokens: fields.IntField = fields.IntField(default=0)
    completion_tokens: fields.IntField = fields.IntField(default=0)
    
    class Meta:
        table = "chat_messages"                                          # 表名