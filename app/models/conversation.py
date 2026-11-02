from tortoise import fields, Model

class Conversation(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="conversations")
    title = fields.CharField(max_length=100, default="新对话")  # 会话标题，默认第一条消息
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "conversations"