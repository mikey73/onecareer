from datetime import datetime, timedelta

from sqlalchemy import func,  MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, object_session
from sqlalchemy.inspection import inspect

from common import errors
from common.compat import get_ident, iteritems
from common.mytypes import MagicDict


# metadata and Base model
convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    # "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

Metadata = MetaData(naming_convention=convention)
Base = declarative_base(metadata=Metadata)
_scope_func = None


def scope_func():
    if _scope_func is None:
        return get_ident()

    return _scope_func()


def set_scope_func(func):
    global _scope_func
    _scope_func = func


# warning: it's a scoped session bind to scope_func
global_session = scoped_session(sessionmaker(), scopefunc=scope_func)


def bind_engine(engine):
    global_session.remove()
    global_session.configure(bind=engine, autoflush=False, expire_on_commit=False)


def load_models_metadata():
    from . import models

    return Base.metadata


def drop_all(engine, tables=None):
    metadata = load_models_metadata()
    metadata.drop_all(bind=engine, tables=tables)


def create_all(engine, tables=None):
    metadata = load_models_metadata()
    metadata.create_all(bind=engine, tables=tables)


def cur_session():
    return global_session()


def remove_session():
    global_session.remove()


def _get(cls, ids):
    multiple = isinstance(ids, (list, tuple, set))
    if not multiple:
        ids = [ids]

    results = []
    for _id in ids:
        if _id is None:
            results.append(None)
            continue

        db_object = cls.query().get(_id)
        if (db_object is not None) and (db_object not in cls.session()):
            obj_session = object_session(db_object)
            if obj_session is not None:
                obj_session.expunge(db_object)

            # noinspection PyBroadException
            try:
                cls.session().add(db_object)
            except:
                db_object = cls.session().merge(db_object)

        results.append(db_object)

    if multiple:
        return results
    else:
        return results[0]


class ModelMixin(object):
    _protect_attrs_ = []
    _to_dict_attrs_ = []
    _not_found_error_ = errors.DBNotFoundError

    @property
    def id(self):
        return self.pk

    @classmethod
    def get_by_ids(cls, ids):
        return _get(cls, ids)

    get_by_id = get_by_ids

    @classmethod
    def session(cls):
        return cur_session()

    @classmethod
    def engine(cls):
        return cls.session().get_bind()

    @classmethod
    def query(cls, fields=None):
        if fields is None:
            return cls.session().query(cls)

        return cls.session().query(fields)

    @classmethod
    def count(cls, conds=None, **filters):
        query = cls.query(func.count(cls.pk)).filter_by(**filters)
        if conds is not None:
            query = query.filter(*conds)
        return query.scalar()

    @classmethod
    def get_all(cls, order=None, offset=None, limit=None, conds=None, **filters):
        return cls.get_query(order=order, offset=offset,
                             limit=limit, conds=conds, **filters).all()

    @classmethod
    def get_query(cls, order=None, offset=None, limit=None, conds=None, **filters):
        query = cls.query().filter_by(**filters)
        if order is not None:
            query = query.order_by(order)
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        if conds is not None:
            query = query.filter(*conds)
        return query

    @classmethod
    def check_exist(cls, conds=None, **filters):
        query = cls.query().filter_by(**filters)
        if conds is not None:
            query = query.filter(*conds)
        return query.count() > 0

    @classmethod
    def get_one(cls, conds=None, **filters):
        query = cls.query().filter_by(**filters)
        if conds is not None:
            query = query.filter(*conds)
        return query.first()

    filter_one = get_one

    @classmethod
    def get_and_check(cls, conds=None, **filters):
        doc = cls.get_one(conds, **filters)
        if not doc:
            raise cls._not_found_error_
        return doc

    @classmethod
    def get_or_create(cls, conds, **create_kwargs):
        obj = cls.get_one(conds=conds)
        if not obj:
            obj = cls.create(**create_kwargs)
            obj.save()
        return obj

    @classmethod
    def create(cls, *args, **kwargs):
        obj = cls(*args, **kwargs)
        return obj

    @classmethod
    def commit(cls):
        """ commit objects in session
        """
        try:
            cls.session().commit()
        except:
            cls.session().rollback()
            raise

    @classmethod
    def columns(cls):
        table = inspect(cls)
        return [c.name for c in table.c]

    def save(self, commit=True):
        self.session().add(self)
        if commit:
            self.commit()
        return self

    def delete(self, commit=True):
        self.session().delete(self)
        if commit:
            self.commit()
        return self

    def update(self, commit=True, **kwargs):
        need_save = False
        for attr, val in iteritems(kwargs):
            if not attr.startswith("_") and (attr not in ("id", "pk")) and (attr in self.__dict__):
                if getattr(self, attr, None) != val:
                    need_save = True
                    setattr(self, attr, val)
            else:
                raise AttributeError("'%s' object has no attribute '%s'" %
                                     (type(self), attr))

        if need_save:
            self.save(commit)

    def to_dict(self, fields=None):
        if fields is None:
            fields = self._to_dict_attrs_ or self.__class__.columns()

        if callable(fields):
            fields = fields()

        _res = MagicDict()
        for k in fields:
            if k in self._protect_attrs_:
                continue
            value = getattr(self, k)
            if callable(value):
                value = value()
            if hasattr(value, "to_dict"):
                value = MagicDict(value.to_dict())
            if not isinstance(value, MagicDict) and isinstance(value, dict):
                value = MagicDict(value)
            _res[k] = value
        if "pk" in _res and "id" not in _res:
            _res["id"] = _res["pk"]
        return _res


class VerifyMixin(ModelMixin):
    @classmethod
    def verify_hash(cls, vhash, expiry=timedelta(weeks=1), set_used=True):
        verify = cls.get_one(vhash=vhash, is_valid=True)
        if verify is None:
            raise errors.InvalidVerification

        earliest = datetime.utcnow() - expiry
        if verify.created < earliest or verify.is_valid is False:
            raise errors.VerificationExpired

        if set_used:
            verify.is_valid = False
            verify.save(commit=True)
        return verify
