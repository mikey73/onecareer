# coding: utf-8
import tornado.web


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