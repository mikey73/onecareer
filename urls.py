# coding: utf-8
from apis.apis import *
from views.views import *

# gather url_patterns from modules
url_patterns = [
    (r"/", IndexHandler),
    (r"/mentors", MentorsHandler),
    (r"/course", CourseHandler),
    (r"/about", AboutHandler),
    (r'/signup', SignupHandler),
    (r'/verify/([0-9a-zA-z]*)', VerifyHandler),
    (r'/login', LoginHandler),
    (r'/logout', LogoutHandler),
    (r"/welcome", WelcomeHandler),
]