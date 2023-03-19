# #########
# # AcuDB #
# #########
#
# # This is an auto-generated Django model module.
# # You'll have to do the following manually to clean this up:
# #   * Rearrange models' order
# #   * Make sure each model has one field with primary_key=True
# #   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
# #   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# # Feel free to rename the models, but don't rename db_table values or field names.
# from django.db import models
#
#
# class Acupoint(models.Model):
#     id = models.TextField(db_column='ID', primary_key=True, blank=True, null=False)  # Field name made lowercase.
#     prc_id = models.TextField(db_column='prcID', unique=True, blank=True, null=True)  # Field name made lowercase.
#     acuname_zh = models.TextField(db_column='acuName_zh', blank=True, null=True)  # Field name made lowercase.
#     acuname_zh_sim = models.TextField(db_column='acuName_zh_sim', blank=True, null=True)  # Field name made lowercase.
#     acuname_en = models.TextField(db_column='acuName_en', blank=True, null=True)  # Field name made lowercase.
#     acuname_tr = models.TextField(db_column='acuName_tr', blank=True, null=True)  # Field name made lowercase.
#     meridian_id = models.TextField(db_column='meridianID', blank=True, null=True)  # Field name made lowercase.
#
#     class Meta:
#         managed = False
#         db_table = 'Acupoint'
#
#
# class Images(models.Model):
#     id = models.TextField(primary_key=True, blank=False, null=False)  # Field name made lowercase.
#     category = models.TextField(blank=False, null=True)
#     source = models.TextField(blank=False, null=True)
#     img = models.BinaryField(blank=True, null=True)
#
#     class Meta:
#         managed = False
#         db_table = 'Images'
#
#
# class Meridian(models.Model):
#     id = models.TextField(db_column='ID', primary_key=True, blank=True)  # Field name made lowercase.
#     meridian_name_zh = models.TextField(db_column='meridianName_zh', blank=True, null=True)  # Field name made lowercase.
#     meridian_name_zh_sim = models.TextField(db_column='meridianName_zh_sim', blank=True, null=True)  # Field name made lowercase.
#     meridian_name_tr = models.TextField(db_column='meridianName_tr', blank=True, null=True)  # Field name made lowercase.
#     meridian_name_en = models.TextField(db_column='meridianName_en', blank=True, null=True)  # Field name made lowercase.
#     meridian_extra = models.BooleanField(db_column='meridianExtra')  # Field name made lowercase.
#
#     class Meta:
#         managed = False
#         db_table = 'Meridian'
#
#
# class AcuAlias(models.Model):
#     acu_id = models.TextField(db_column='acuID', blank=True, null=True)  # Field name made lowercase.
#     alias_name = models.TextField(db_column='aliasName', blank=True, null=True)  # Field name made lowercase.
#     alias_src = models.TextField(db_column='aliasSrc', blank=True, null=True)  # Field name made lowercase.
#
#     class Meta:
#         managed = False
#         db_table = 'acuAlias'
#
#
# class AcuEx(models.Model):
#     id = models.TextField(primary_key=True, db_column='ID', blank=True, null=False)  # Field name made lowercase.
#     bypass = models.ForeignKey(Acupoint, models.DO_NOTHING, db_column='bypass', blank=True, null=True)
#     meridian_id = models.ForeignKey(Meridian, models.DO_NOTHING, db_column='meridianID', blank=True, null=True)  # Field name made lowercase.
#
#     class Meta:
#         managed = False
#         db_table = 'acuEx'
#
#
# class AcuFind(models.Model):
#     acu_id = models.TextField(db_column='acuID', blank=True, null=True)  # Field name made lowercase.
#     acufind_desc = models.TextField(db_column='acuFind_desc', blank=True, null=True)  # Field name made lowercase.
#     ref = models.TextField(blank=True, null=True)
#
#     class Meta:
#         managed = False
#         db_table = 'acuFind'
#
#
# class AcuLoc(models.Model):
#     acu_id = models.TextField(db_column='acuID', blank=True, null=True)  # Field name made lowercase.
#     aculoc_desc = models.TextField(db_column='acuLoc_desc', blank=True, null=True)  # Field name made lowercase.
#     aculoc_pos = models.TextField(db_column='acuLoc_pos', blank=True, null=True)  # Field name made lowercase.
#
#     class Meta:
#         managed = False
#         db_table = 'acuLoc'
#
#
# class ImgLink(models.Model):
#     id = models.AutoField(primary_key=True, db_column='ID', blank=True, null=False)  # Field name made lowercase.
#     img_id = models.TextField(db_column='imgID', blank=True, null=True)  # Field name made lowercase.
#     ref_id = models.TextField(db_column='refID', blank=True, null=True)  # Field name made lowercase.
#     img_cat = models.ForeignKey(Images, related_name='category', db_column='imgCAT', blank=True, null=True)  # Field name made lowercase.
#     img_src = models.TextField(db_column='imgSRC', blank=True, null=True)  # Field name made lowercase.
#     img_desc = models.TextField(blank=True, null=True)
#
#     class Meta:
#         managed = False
#         db_table = 'imgLink'
#
#
# class MeridianRoute(models.Model):
#     meridian_id = models.TextField(db_column='meridianID', blank=True, null=True)  # Field name made lowercase.
#     route = models.TextField(blank=True, null=True)
#     route_src = models.TextField(blank=True, null=True)
#     route_classic = models.TextField(blank=True, null=True)
#
#     class Meta:
#         managed = False
#         db_table = 'meridianRoute'

##############
# DEFAULT DB #
##############

# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models

class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)
    name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()
    first_name = models.CharField(max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    action_flag = models.PositiveSmallIntegerField()

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'
