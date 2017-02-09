# coding: utf-8
from basehandlers import BaseHandler,AuthRequiredViewHandler
import models as db
from common import errors

class ViewHandler(BaseHandler):
    url_patterns = (
        # pattern,     action name,  HTTP method(s)
        ["mentors/?$", "mentors", ("GET",)],
        ["course/?$", "course", ("GET",)],
        ["about/?$", "about", ("GET",)],
        ["login/?$", "login", ("GET",)],
        ["signup/?$", "signup", ("GET",)],
        ["verify/?([0-9a-zA-z]*)/?$", "verify", ("GET",)],
    )

    def mentors(self):
        self.render("mentors.html")

    def course(self):
        self.render('course.html')

    def about(self):
        self.render('about.html')

    def login(self):
        self.render('login.html')

    def signup(self):
        self.render('signup.html')

    def verify(self, vhash=None):
        self.render('verify.html', vhash=vhash)


class AuthViewHandler(AuthRequiredViewHandler):
    """ SettingsHandler, all actions are auth required """
    url_patterns = (
        # pattern,     action name,  HTTP method(s)
        ["welcome/?$", "welcome", ("GET", "POST")],
    )

    def welcome(self):
        try:
            account = self.get_cur_account()
            account_info = account.to_dict()
            self.render("welcome.html", account_info=account.fullname)
        except errors.AccountPermissionError:
            self.render('login.html')