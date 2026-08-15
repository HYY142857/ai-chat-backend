from tortoise import fields, Model

class FileRecord(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="file_records")  # 外键，指向 User
    original_name = fields.CharField(max_length=255)     # 原始文件名
    saved_name = fields.CharField(max_length=255)        # UUID 重命名后的文件名
    file_size = fields.IntField()                         # 文件大小（字节）
    content = fields.TextField(null=True)                 # 提取出来的文字内容
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "file_records"  # 表名