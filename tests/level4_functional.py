'''
Created on Mar 3, 2014

@author: steve
'''
import webtest
from urllib.parse import urlparse
import unittest
from webtest import TestApp
import bottle
from bottle.ext import sqlite, beaker
import sqlite3
import os

import main
import database


DATABASE_NAME = "test.db"
main.app.install(sqlite.Plugin(dbfile=DATABASE_NAME))

# make sure bottle looks for templates in the main directory, not this one
bottle.TEMPLATE_PATH = [os.path.join(os.path.dirname(__file__), p) for p in ['../', '../views/']]


class Level3FunctionalTests(unittest.TestCase):

    def setUp(self):

        session_opts = {
            'session.type': 'memory',
        }
        beaker_app = beaker.middleware.SessionMiddleware(main.app, session_opts)
        db = sqlite3.connect(DATABASE_NAME)
        database.create_tables(db)
        self.users, self.images = database.sample_data(db)
        self.app = TestApp(beaker_app)
        bottle.debug() # force debug messages in error pages returned by webtest

    def tearDown(self):
        pass

    def doLogin(self, email, password):
        """Perform a login,
         returns the response to the login request"""

        response = self.app.get('/')

        loginform = response.forms['loginform']

        loginform['nick'] = email
        loginform['password'] = password

        return loginform.submit()

    def testMyImagesForm(self):
        """As a registered user, when I load the "My Images" page I see a form that has
         a file selection input and a button labelled "Upload Image".
        """

        imagefilename = "iceland.jpg"

        (password, nick, avatar) = self.users[0]

        # login and then get the my images page
        self.doLogin(nick, password)
        response = self.app.get('/my')

        # the page should contain an upload form
        self.assertIn('uploadform', response.forms)

        form = response.forms['uploadform']
        # action should be /upload
        self.assertEqual('/upload', form.action)

        # try uploading a file
        form['imagefile'] = webtest.Upload(imagefilename, content_type='image/jpeg')

        response = form.submit()

        # expect a redirect to the /my page

        self.assertIn(response.status, ['303 See Other', '302 Found'])
        (_, _, path, _, _, _) = urlparse(response.headers['Location'])
        self.assertEqual('/my', path)

        # and when I retrieve that page I see my image at the top
        response = self.app.get('/my')

        flowtows = response.html.find_all(class_='flowtow')
        # should find my image in the first one
        div = flowtows[0]
        img = div.find("img")
        # should be the image src attribute
        self.assertIn(imagefilename, img['src'])

        # and we should be able to retrieve it
        #response = self.app.get(img['src'])

        #self.assertEqual("200 OK", response.status)

        # remove the uploaded image
        os.unlink('../static/images/iceland.jpg')

    def testMyImagesFormNoLogin(self):
        """ As an unregistered user (not logged in) if I try to upload an image by
        accessing the /upload URL directly, I get a redirect response back to the home page.

        """

        imagefilename = "iceland.jpg"

        (password, nick, avatar) = self.users[0]

        # login and then get the my images page
        self.doLogin(nick, password)
        response = self.app.get('/my')

        # the page should contain an upload form
        self.assertIn('uploadform', response.forms)

        form = response.forms['uploadform']
        # action should be /upload
        self.assertEqual('/upload', form.action)

        # try uploading a file
        form['imagefile'] = webtest.Upload(imagefilename, content_type='image/jpeg')


        # before we submit, we'll logout

        logoutform = response.forms['logoutform']
        response3 = logoutform.submit()

        # now submit the form as a regular user

        response = form.submit()

        # expect a redirect to the / page
        self.assertIn(response.status, ['303 See Other', '302 Found'])
        (_, _, path, _, _, _) = urlparse(response.headers['Location'])
        self.assertEqual('/', path,  "expected redirect to '/' after non-login file upload")

        # and when I retrieve that page I should not see the image
        response = self.app.get('/')

        imgs = response.html.find_all('img')
        for img in imgs:
           self.assertNotIn(imagefilename, img['src'], "found image that should not have uploaded")




if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main(warnings='ignore')