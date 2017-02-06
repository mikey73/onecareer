from sqlalchemy import Column, Integer, String, Text, text, Enum, Boolean, DateTime, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from .constants import AccountRoles
from config import *

Model = declarative_base()
engine = create_engine(db_url)
DBSession = sessionmaker(bind=engine)

class Account(Model):
    __tablename__ = "account"

    pk = Column(Integer, primary_key=True)
    fullname = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    password = Column(String, nullable=False)
    joined = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    is_valid = Column(Boolean, nullable=False, server_default=text("false"))
    role = Column(Enum(*AccountRoles.values(), name="roles"), nullable=False)

    def __init__(self):
        pass

    def columns(self):
        return [c.name for c in self.__table__.columns]

    def to_dict(self):
        return dict([(c, getattr(self, c)) for c in self.columns()])