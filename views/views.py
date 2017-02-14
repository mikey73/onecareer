# coding: utf-8
from basehandlers import BaseHandler


class IndexHandler(BaseHandler):
    def get(self):
        self.render('index.html', is_login=self.is_login())


class MentorsHandler(BaseHandler):
    def get(self):
        self.render('mentors.html', is_login=self.is_login())


class CourseHandler(BaseHandler):
    def get(self):
        self.render('course.html', is_login=self.is_login())


class AboutHandler(BaseHandler):
    def get(self):
        self.render('about.html', is_login=self.is_login())