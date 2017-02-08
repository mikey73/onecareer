from basehandlers import BaseHandler


class ViewHandler(BaseHandler):
    url_patterns = (
        # pattern,     action name,  HTTP method(s)
        ["mentors/?$", "mentors", ("GET",)],
        ["course/?$", "course", ("GET",)],
        ["about/?$", "about", ("GET",)],
        ["login/?$", "login", ("GET",)],
        ["signup/?$", "signup", ("GET",)],
        ["welcome/?$", "welcome", ("POST",)],
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

    def welcome(self):
         info = self.get_argument('info')
         self.render('welcome.html', info=info)

    def verify(self, vhash=None):
        self.render('verify.html', vhash=vhash)