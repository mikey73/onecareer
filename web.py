import os.path
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.options import define, options
import tornado.autoreload

define("port", default=8888, help="run on the given port", type=int)
define("debug", default=True, help="Debug Mode",type=bool)


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html')


class MentorsHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('mentors.html')


class CourseHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('course.html')


class AboutHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('about.html')


class LoginHandler(tornado.web.RequestHandler):
    def get(self, input):
        self.render('login.html', target=input)


class WelcomeHandler(tornado.web.RequestHandler):
    def post(self):
        username = self.get_argument('username')
        password = self.get_argument('password')

        self.render('welcome.html', username=username, password=password)


class SignupHandler(tornado.web.RequestHandler):
    def get(self, input):
        self.render('signup.html', target=input)


class ValidateCodeHandler(tornado.web.RequestHandler):
    def get(self, input):
        self.redirect('http://www.qv12197932.icoc.me/validateCode.jsp')


if __name__ == '__main__':
    tornado.options.parse_command_line()
    app = tornado.web.Application(
        handlers=[(r'/', IndexHandler),
                  (r'/mentors', MentorsHandler),
                  (r'/course', CourseHandler),
                  (r'/about', AboutHandler),
                  (r'/login/(\w+)', LoginHandler),
                  (r'/signup/(\w+)', SignupHandler),
                  (r'/welcome', WelcomeHandler),
                  (r'/signup/validateCode(.*)', ValidateCodeHandler),
                  ],
        template_path=os.path.join(os.path.dirname(__file__), "templates",),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
    )
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()