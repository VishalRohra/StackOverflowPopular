"""
Python implementation of Twitter bot fetching Popular Stackoverflow Posts
Made by Vishal Rohra (http://www.github.com/vishalrohra)
28th May'17
"""

# Import modules
import tweepy
import requests
import sqlite3 as lite
from random import randint
import HTMLParser  # for Python 2.x. 'import html' for Python 3.X
from secrets import consumer_key, consumer_secret, access_token, access_token_secret, stack_exchange_key

# Global variables
important_tags = ['javascript', 'java', 'php', 'c++', 'c#', 'android', 'python', 'html', 'ios', 'css', 'sql', 'objective_c', 'c', 'ruby', 'swift']
MIN_THRESHOLD = 300  # Minimum threshold of what score counts as popular
ALL_ITEMS = 'items'
DB_NAME = 'test.db'
PAGE_SIZE = 100
TAG_LENGTH = 36
LINK_LENGTH = 24


def build_default_params(order, pagesize=PAGE_SIZE, is_answered=True, sort='votes', site='stackoverflow'):
    parameters = {"site": site,
                  "sort": sort,
                  "order": order,
                  "is_answered": is_answered,
                  "pagesize": pagesize}
    return parameters


def build_data(base_url, object_, parameters):
    response = requests.get(base_url + '/' + object_, params=parameters)
    data = response.json()
    return data


def get_most_popular(url):
    parameters = build_default_params('desc')
    data = build_data(url, 'questions', parameters)
    highest_score = data[ALL_ITEMS][PAGE_SIZE - 1]['score']
    return highest_score


def fetch_valid_post(data):
    for index in range(0, PAGE_SIZE - 1):
        R_INDEX = randint(0, PAGE_SIZE - 1)
        is_answered = data[ALL_ITEMS][R_INDEX]['is_answered']
        not_in_database = check_within_db(data[ALL_ITEMS][R_INDEX]['question_id'])
        if is_answered and not_in_database:
            return R_INDEX, True
    return R_INDEX, False


def create_db():
    conn = lite.connect(DB_NAME)
    with conn:
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS log")
        cur.execute("CREATE TABLE log(Id INT, Title TEXT, Link TEXT, Tags TEXT, Score INT)")


def commit_to_db(essential_json):
    conn = lite.connect(DB_NAME)
    with conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO log VALUES (:question_id, :title, :link, :tags, :score)", {'question_id': essential_json['question_id'], 'title': essential_json['title'], 'link': essential_json['link'], 'tags': ','.join(essential_json['tags']), 'score': essential_json['score']})


def check_within_db(value):
    conn = lite.connect(DB_NAME)
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM log WHERE Id=:value", {'value': value})
        row_count = cur.fetchone()
        if row_count:
            return False
        else:
            return True


def get_tags(essential_json):
    tag_list = essential_json['tags']
    prefix_string = ""
    tag_string = ""
    all_length = 0
    index = 0
    while (all_length < TAG_LENGTH) and (index < len(tag_list)):
        keyword = tag_list[index].replace("-", "_")
        if not prefix_string and (keyword in important_tags):
            keyword = keyword.replace("#", "sharp")
            keyword = keyword.replace("+", "plus")
            prefix_string = prefix_string + '#' + keyword + '_SOP: '
            all_length = all_length + len(prefix_string)
        else:
            tag_string = tag_string + '#' + keyword + ' '
            all_length = all_length + len(tag_string)
        index = index + 1
    tag_string = tag_string + '#stackoverflow #SOP '
    return prefix_string, tag_string


def get_title(essential_json, len_tags):
    len_links = LINK_LENGTH
    permitted_title_len = 140 - (len_links + len_tags + 3)
    h = HTMLParser.HTMLParser()
    org_title = h.unescape(essential_json['title'])  # For Python 3.x, html.unescape(essential_json['title'])
    title_string = (org_title[:permitted_title_len] + '.. ') if len(org_title) > (permitted_title_len + 3) else org_title + ' '
    return title_string


def generate_tweet(essential_json):
    prefix, tags = get_tags(essential_json)
    len_tags = len(prefix) + len(tags)
    title = get_title(essential_json, len_tags)
    link = essential_json['link']
    tweet_string = prefix + title + tags + link
    return tweet_string


def tweet_away(tweet):
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)
    api.update_status(tweet)


def main():

    # Global variables
    base_url = 'http://api.stackexchange.com/2.2'
    is_answer_fetched = False

    # Setup database. Comment out after first iteration.
    create_db()

    while not is_answer_fetched:

        # Generate random minimum number
        MAX_THRESHOLD = get_most_popular(base_url)
        R_MIN = randint(MIN_THRESHOLD, MAX_THRESHOLD)

        # Build parameters. API Ref: http://api.stackexchange.com/docs/types/question
        parameters = build_default_params('asc', pagesize=PAGE_SIZE)
        parameters.update({'min': R_MIN})
        parameters.update({'key': stack_exchange_key})

        # Build data.json
        data = build_data(base_url, 'questions', parameters)

        # Fetch valid post
        R_INDEX, is_answer_fetched = fetch_valid_post(data)

        # If valid, update dict with essential key/value pairs
        essential_json = {}
        essential_list = ['question_id', 'title', 'link', 'tags', 'score']
        if is_answer_fetched:
            single_json = data[ALL_ITEMS][R_INDEX]
            for item in single_json:
                if item in essential_list:
                    essential_json.update({item: single_json[item]})
            break

    # Insert essential json to db
    commit_to_db(essential_json)

    # Generate tweet
    tweet = generate_tweet(essential_json)

    # Tweet away
    tweet_away(tweet)


if __name__ == '__main__':
    main()
