import sqlalchemy as sa
from sqlalchemy.orm import relationship
from .constants import *
from .base import *
import functools
import bcrypt
from common.utils import gen_uuid_str


class Account(Base, ModelMixin):
    __tablename__ = "account"
    __table_args__ = (
        sa.UniqueConstraint('email', 'api_pk'),
    )
    _not_found_error_ = errors.AccountNotFoundError
    _protect_attrs_ = ["password", "verify"]
    _to_dict_attrs_ = ["pk", "api_pk", "fullname", "email", "joined",
                       "is_active", "is_valid", "role"]

    pk = sa.Column(sa.Integer, primary_key=True)
    api_pk = sa.Column(sa.Integer, sa.ForeignKey("api.pk"), nullable=False)
    fullname = sa.Column(sa.String, nullable=False)
    email = sa.Column(sa.String, nullable=False, index=True)
    password = sa.Column(sa.String, nullable=False)
    joined = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow)
    is_active = sa.Column(sa.Boolean, nullable=False, default=True)
    is_valid = sa.Column(sa.Boolean, nullable=False, default=False)
    role = sa.Column(sa.Enum(*AccountRoles.values(), name="roles"), nullable=False)
    verify = relationship("Verification", uselist=False, backref="account")
    logs = relationship("APILog", backref="account", cascade="all, delete-orphan")

    @classmethod
    def new(cls, email, password, fullname, role, api_pk):
        if cls.check_exist(email=email, role=role, api_pk=api_pk):
            raise errors.EmailExistsError

        new_verify = Verification()
        new_account = cls.create(email=email, password=password, fullname=fullname,
                                 role=role, api_pk=api_pk, verify=new_verify)
        new_account.set_password(password)
        new_verify.save(commit=False)
        new_account.save(commit=True)

        return new_account

    @classmethod
    def renew_verification(cls, email, role, api_pk):
        account = cls.get_and_check(email=email, role=role, api_pk=api_pk)
        if not account:
            raise errors.EmailNotFoundError

        account.verify.delete(commit=False)
        account.verify = Verification()
        account.verify.save(commit=False)
        account.save(commit=True)
        return account.verify

    def set_password(self, password):
        self.password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    def check_password(self, password):
        return self.password == bcrypt.hashpw(
            password.encode("utf-8"),
            self.password.encode("utf-8")
        )


class Verification(Base, VerifyMixin):
    __tablename__ = "verification"
    _to_dict_attrs_ = ["pk", "vhash", "created"]

    pk = sa.Column(sa.Integer, primary_key=True)
    account_pk = sa.Column(sa.Integer, sa.ForeignKey("account.pk"))
    vhash = sa.Column(sa.String, unique=True, nullable=False,
                      default=functools.partial(gen_uuid_str, "", 16))
    created = sa.Column(sa.DateTime, nullable=False,
                        default=datetime.utcnow)
    is_valid = sa.Column(sa.Boolean, nullable=True, default=True)


class APILog(Base, ModelMixin):
    __tablename__ = "api_log"

    _to_dict_attrs_ = ["pk", "account_pk", "path", "method",
                       "start_ts", "runtime", "status", "msg", "error_code"]

    pk = sa.Column(sa.Integer, primary_key=True)
    account_pk = sa.Column(sa.Integer, sa.ForeignKey("account.pk"))
    path = sa.Column(sa.String, nullable=False)
    method = sa.Column(sa.String, nullable=False)
    start_ts = sa.Column(sa.DateTime, nullable=False,
                         default=datetime.utcnow)
    runtime = sa.Column(sa.Float, nullable=True)
    status = sa.Column(sa.SmallInteger, nullable=False)
    msg = sa.Column(sa.String, nullable=False)
    error_code = sa.Column(sa.SmallInteger, nullable=True)


class API(Base, ModelMixin):
    __tablename__ = "api"

    _to_dict_attrs_ = ["pk", "client_id", "client_secret",
                       "is_admin", "is_active", "charge", "site"]

    pk = sa.Column(sa.Integer, primary_key=True)
    client_id = sa.Column(sa.String, index=True)
    client_secret = sa.Column(sa.String)
    is_admin = sa.Column(sa.Boolean, default=False)
    is_active = sa.Column(sa.Boolean, default=True)
    charge = sa.Column(sa.Numeric, nullable=False, default=0.0)
    site = sa.Column(sa.Enum(*APISites.values(), name="sites"), nullable=True)
    accounts = relationship("Account", backref="api")
    is_frontend = sa.Column(sa.Boolean, default=False)
    is_developer = sa.Column(sa.Boolean, default=False)

    @classmethod
    def new(cls, client_id=None, client_secret=None, **kwargs):
        client_id = client_id or gen_uuid_str(length=32)
        client_secret = client_secret or gen_uuid_str(length=44)
        new_api = cls(client_id=client_id, client_secret=client_secret, **kwargs)
        new_api.save()
        return new_api

    @classmethod
    def exists(cls, client_id, client_secret):
        return cls.check_exist(client_id=client_id, client_secret=client_secret)