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


class AccountIndustries(BaseStatus):
    IT = "IT"
    Finance = "Finance"
    Both = "Both"


class AccountSignupSource(BaseStatus):
    Site = "Site"
    Linkedin = "Linkedin"


USStates = (
    "AA", "AE", "AK", "AL", "AP", "AR", "AS", "AZ", "CA", "CO", "CT", "DC", "DE",
    "FM", "FL", "GA", "GU", "HI", "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA", "MD",
    "ME", "MH", "MI", "MN", "MO", "MP", "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM",
    "NV", "NY", "OH", "OK", "OR", "PA", "PR", "PW", "RI", "SC", "SD", "TN", "TX", "UT",
    "VA", "VI", "VT", "WA", "WI", "WV", "WY"
)