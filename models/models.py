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
        sa.UniqueConstraint('email'),
    )
    _not_found_error_ = errors.AccountNotFoundError
    _protect_attrs_ = ["password", "verify"]
    _to_dict_attrs_ = ["pk", "fullname", "email", "joined",
                       "is_active", "is_valid", "role", "signup_source"]

    pk = sa.Column(sa.Integer, primary_key=True)
    fullname = sa.Column(sa.String, nullable=False)
    email = sa.Column(sa.String, nullable=False, index=True)
    password = sa.Column(sa.String, nullable=False)
    joined = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow)
    is_active = sa.Column(sa.Boolean, nullable=False, default=True)
    is_valid = sa.Column(sa.Boolean, nullable=False, default=False)
    role = sa.Column(sa.Enum(*AccountRoles.values(), name="roles"), nullable=False)
    signup_source = sa.Column(sa.Enum(*AccountSignupSource.values(), name="signup_sources"), nullable=False,
                              default=AccountSignupSource.Site)
    verify = relationship("Verification", uselist=False, backref="account")

    @classmethod
    def new(cls, email, password, fullname, role, signup_source=AccountSignupSource.Site):
        if cls.check_exist(email=email, signup_source=signup_source):
            raise errors.EmailExistsError

        new_verify = Verification()
        new_account = cls.create(email=email, password=password, fullname=fullname,
                                 role=role, signup_source=signup_source, verify=new_verify)
        new_account.set_password(password)
        new_verify.save(commit=False)
        new_account.save(commit=True)

        return new_account

    @classmethod
    def renew_verification(cls, email, role):
        account = cls.get_and_check(email=email, role=role)
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