from basehandlers import BaseHandler


class ViewHandler(BaseHandler):
    url_patterns = (
        # pattern,     action name,  HTTP method(s)
        ["index/?$", "index", ("GET", )],
        ["mentors/?$", "mentors", ("GET",)],
        ["course/?$", "course", ("GET",)],
        ["about/?$", "about", ("GET",)],
        ["login/?(\w+)/?$", "login", ("GET",)],
        ["signup/?(\w+)/?$", "signup", ("GET",)],
    )

    def index(self):
        self.render('index.html')

    def mentors(self):
        self.render("mentors.html")

    def course(self):
        self.render('course.html')

    def about(self):
        self.render('about.html')

    def login(self, target=None):
        self.render('login.html', target=target)

    def signup(self, target=None):
        self.render('signup.html', target=target, info="")