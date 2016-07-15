from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import parser
from urlparse import urljoin
from flask import Flask
from flask import Response
from flask import render_template
from flask import request
from google.appengine.ext import ndb
from google.appengine.api import mail
from google.appengine.api import urlfetch
from werkzeug.contrib.atom import AtomFeed

import feedparser
import pprint
import re
import traceback
import pytz


# TODO new approach

# Use the existing RSS daily digest (from either IFTTT or the other site)
# but make this an RSS digest composer --- interlacing new posts from other feeds


app = Flask(__name__)
app.config['DEBUG'] = True


DEFAULT_KEY = 'jesse.gunsch@gmail.com'



class Feed(ndb.Model):
  """Sub model for representing a stored feed."""
  url = ndb.StringProperty(indexed=True)


@app.route('/')
def hello():
    """Lists the stored feeds."""
    values = get_feeds()
    return 'feeds: ' + '<br/>'.join(map(str,values))

def get_feeds():
    values_query = Feed.query(ancestor=parent_key())
    return values_query.fetch(100)

def parent_key():
  return ndb.Key('User', DEFAULT_KEY)

def get_recent_posts(filter_recent=False):
  feeds = get_feeds()
  posts = []

  for feed in feeds:
    result = feedparser.parse(feed.url)
    for entry in result['entries']:
      try:
        # entry['content'] should be an array
        if 'content' in entry:
          html_contents = filter(lambda content: 'html' in content['type'], entry['content'])
          if not html_contents:
            continue
          html_content = html_contents[0]
        elif 'summary_detail' in entry:
          html_content = entry['summary_detail']
        else:
          raise Exception('not sure whats going on here')
        post = {
          'author': entry['author'] if 'author' in entry else '',
          'content': html_content['value'],
          'content_type': html_content['type'],
          'url': entry['link'],
          'published': parser.parse(entry['published']),
          'title': '%s (%s)' % (entry['title'], result['feed']['title'])
        }
        if 'updated' in entry:
          post['updated'] = parser.parse(entry['updated'])
        if not filter_recent or pytz.UTC.localize(datetime.now()) - post['published'] < timedelta(1):
          posts.append(post)
      except Exception as e:
        pprint.pprint(entry)
        raise e
        break

  return sorted(posts, key=lambda post: post['published'], reverse=True)

@app.route('/insert')
def insert():
  url = request.args.get('url')
  if not url:
    return 'need url parameter'

  Feed.get_or_insert(url, parent=parent_key(), url=url)
  return 'inserted ' + url

@app.route('/raw_posts')
def raw_posts():
  posts = get_recent_posts(filter_recent=True)
  return Response(pprint.pformat(posts), mimetype='text/plain')

def make_external(url):
  return urljoin(request.url_root, url)

def add_post_to_feed(feed, post):
  # TODO: ignoring content_type right now
  feed.add(post['title'], unicode(post['content']),
           content_type='html',
           author=post['author'],
           url=make_external(post['url']),
           updated=post['updated'] if 'updated' in post else post['published'],
           published=post['published'])

@app.route('/last24hr')
def last_24_hr():
  posts = get_recent_posts(filter_recent=True)
  feed = AtomFeed('Recent Articles',
                  feed_url=request.url, url=request.url_root)
  for post in posts:
    add_post_to_feed(feed, post)
  return feed.get_response()

@app.route('/feed')
def feed():
  posts = get_recent_posts(filter_recent=False)
  feed = AtomFeed('All Articles',
                  feed_url=request.url, url=request.url_root)
  for post in posts:
    add_post_to_feed(feed, post)
  return feed.get_response()

def handle_error(scraper):
  error = traceback.format_exc()
  mail.send_mail(
      'jesse.gunsch@gmail.com',
      'jesse.gunsch@gmail.com',
      'scraper failed: ' + scraper,
      'error: ' + error)
  raise

@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, nothing at this URL.', 404
