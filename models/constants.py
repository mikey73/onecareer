class BaseStatus(object):
    @classmethod
    def values(cls):
        if not getattr(cls, "__values__", None):
            cls.__values__ = [getattr(cls, name)
                              for name in dir(cls)
                              if name and not name.startswith("_") and
                              not callable(getattr(cls, name))]
        return cls.__values__


class AccountRoles(BaseStatus):
    Talent = "Talent"
    Mentor = "Mentor"
    HR = "HR"
    TBD = "TBD"

class AccountSignupSource(BaseStatus):
    Site = "Site"
    Linkedin = "Linkedin"