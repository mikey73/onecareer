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
        sa.UniqueConstraint('email', 'signup_source'),
    )
    _not_found_error_ = errors.AccountNotFoundError
    _protect_attrs_ = ["password", "verify", "account_info"]
    _to_dict_attrs_ = ["pk", "fullname", "email", "joined", "is_active",
                       "is_valid", "role", "industry", "signup_source"]

    pk = sa.Column(sa.Integer, primary_key=True)
    fullname = sa.Column(sa.String, nullable=False)
    email = sa.Column(sa.String, nullable=False, index=True)
    password = sa.Column(sa.String, nullable=False)
    joined = sa.Column(sa.DateTime, nullable=False, default=datetime.utcnow)
    is_active = sa.Column(sa.Boolean, nullable=False, default=True)
    is_valid = sa.Column(sa.Boolean, nullable=False, default=False)
    role = sa.Column(sa.Enum(*AccountRoles.values(), name="roles"), nullable=False)
    industry = sa.Column(sa.Enum(*AccountIndustries.values(), name="industries"), nullable=False,
                         default=AccountIndustries.Both)
    signup_source = sa.Column(sa.Enum(*AccountSignupSource.values(), name="signup_sources"), nullable=False,
                              default=AccountSignupSource.Site)
    verify = relationship("Verification", uselist=False, backref="account")
    account_info = relationship("AccountInfo", uselist=False,
                                backref="account", cascade="all, delete-orphan")
    work_experience = relationship("WorkExperience", uselist=False,
                                backref="account", cascade="all, delete-orphan")
    education = relationship("Education", uselist=False,
                                backref="account", cascade="all, delete-orphan")

    @classmethod
    def new(cls, email, password, fullname, role, is_valid=False, signup_source=AccountSignupSource.Site):
        if cls.check_exist(email=email, signup_source=signup_source):
            raise errors.EmailExistsError

        new_verify = Verification()
        new_account = cls.create(email=email, password=password, fullname=fullname, role=role,
                                 is_valid=is_valid, signup_source=signup_source, verify=new_verify)
        new_account.set_password(password)
        new_verify.save(commit=False)
        new_account.save(commit=True)

        return new_account

    @classmethod
    def renew_verification(cls, email, role):
        account = cls.get_and_check(email=email, signup_source=AccountSignupSource.Site)
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

    def get_settings(self):
        resp = MagicDict({
            "pk": self.pk,
            "fullname": self.fullname,
            "email": self.email,
            "role": self.role,
            "industry": self.industry,
            "phone_num": "",
            "wechat": "",
            "avatar_uri": "",
            "address_line1": "",
            "address_line2": "",
            "city": "",
            "state": "",
        })
        if self.account_info:
            resp.update(self.account_info.to_dict())
        return resp

    def update_settings(self, **settings):
        account_cols = Account.columns()
        acc_info_cols = AccountInfo.columns()

        for key in settings:
            if key in account_cols:
                setattr(self, key, settings[key])
                continue

            if key in acc_info_cols:
                if not self.account_info:
                    self.account_info = AccountInfo()
                setattr(self.account_info, key, settings[key])
                continue


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


class AccountInfo(Base, ModelMixin):
    __tablename__ = "account_info"

    _to_dict_attrs_ = ["phone_num", "wechat", "avatar_uri",
                       "address_line1", "address_line2", "city", "state"]

    States = USStates

    pk = sa.Column(sa.Integer, primary_key=True)
    account_pk = sa.Column(sa.Integer, sa.ForeignKey("account.pk"))
    phone_num = sa.Column(sa.String, nullable=True)
    wechat = sa.Column(sa.String, nullable=True)
    avatar_uri = sa.Column(sa.String, nullable=True)
    address_line1 = sa.Column(sa.String, nullable=True)
    address_line2 = sa.Column(sa.String, nullable=True)
    city = sa.Column(sa.String, nullable=True)
    state = sa.Column(sa.Enum(*USStates, name="states"), nullable=True)


class WorkExperience(Base, ModelMixin):
    __tablename__ = "work_experience"

    _to_dict_attrs_ = ["pk", "company", "title", "start_time",
                       "end_time", "description"]

    pk = sa.Column(sa.Integer, primary_key=True)
    account_pk = sa.Column(sa.Integer, sa.ForeignKey("account.pk"))
    company = sa.Column(sa.String, nullable=False)
    title = sa.Column(sa.String, nullable=False)
    start_time = sa.Column(sa.String, nullable=False)
    end_time = sa.Column(sa.String, nullable=False)
    description = sa.Column(sa.String, nullable=False)

    @classmethod
    def get_work_experience_by_account(cls, account_pk, order=None, offset=None, limit=None):
        query = cls.get_query(order=order, offset=offset, limit=limit, account_pk=account_pk)
        return query.filter().all()


class Education(Base, ModelMixin):
    __tablename__ = "education"

    _to_dict_attrs_ = ["pk", "university", "degree", "graduation_year"]

    pk = sa.Column(sa.Integer, primary_key=True)
    account_pk = sa.Column(sa.Integer, sa.ForeignKey("account.pk"))
    university = sa.Column(sa.String, nullable=False)
    degree = sa.Column(sa.String, nullable=False)
    graduation_year = sa.Column(sa.String, nullable=False)

    @classmethod
    def get_education_by_account(cls, account_pk, order=None, offset=None, limit=None):
        query = cls.get_query(order=order, offset=offset, limit=limit, account_pk=account_pk)
        return query.filter().all()