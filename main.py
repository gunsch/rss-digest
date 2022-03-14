from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import parser
from urllib.parse import urljoin
from flask import Flask
from flask import Response
from flask import render_template
from flask import request
from feedwerk.atom import AtomFeed

import feedparser
import os
import pprint
import traceback
import pytz

from config import FEEDS

app = Flask(__name__)
app.config['DEBUG'] = True


@app.route('/')
def hello():
  """Lists the stored feeds."""
  return 'feeds: ' + '<br/>'.join(FEEDS)

def get_recent_posts(filter_recent=False):
  posts = []

  for feed in FEEDS:
    result = feedparser.parse(feed)
    for entry in result['entries']:
      try:
        # entry['content'] should be an array
        if 'content' in entry:
          html_contents = filter(lambda content: 'html' in content['type'], entry['content'])
          if not html_contents:
            continue
          html_content = list(html_contents)[0]
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

@app.route('/raw_posts')
def raw_posts():
  posts = get_recent_posts(filter_recent=True)
  return Response(pprint.pformat(posts), mimetype='text/plain')

def make_external(url):
  return urljoin(request.url_root, url)

def add_post_to_feed(feed, post):
  # TODO: ignoring content_type right now
  feed.add(post['title'], post['content'],
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
  # Oh no, no errors now
  # mail.send_mail(
  #     'jesse.gunsch@gmail.com',
  #     'jesse.gunsch@gmail.com',
  #     'scraper failed: ' + scraper,
  #     'error: ' + error)
  raise

@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, nothing at this URL.', 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
