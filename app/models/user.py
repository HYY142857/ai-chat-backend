from tortoise.models import Model
from tortoise import fields


class User(Model):
    id = fields.IntField(pk=True)        # 整数主键，自动递增
    username = fields.CharField(max_length=20, unique=True)  # 字符串，不能重复
    password = fields.CharField(max_length=128)              # 存哈希后的密码
    created_at = fields.DatetimeField(auto_now_add=True)     # 创建时自动填当前时间

    class Meta:
        table = "users"  # 告诉 Tortoise 这张表在数据库里叫什么