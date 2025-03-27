import os
from collections import namedtuple

from flask import Flask, render_template, request, redirect, url_for
import json
import redis

STORAGE = 'redis'

app = Flask(__name__)
FILE_PATH = 'shopping_list.json'
CATEGORY_FILE = 'categories.json'

REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

redis_client = redis.StrictRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    # decode_responses=True,
  ssl=True
)

data = {'shopping_list': [],
        'categories': {
            'milk': 'dairy', 'cheese': 'dairy', 'yogurt': 'dairy',
            'beef': 'meat', 'chicken': 'meat', 'pork': 'meat',
            'bell pepper': 'fruit and vegetables', 'apple': 'fruit and vegetables', 'carrot': 'fruit and vegetables',
            'bread': 'bakery', 'bagel': 'bakery', 'croissant': 'bakery',
            'rice': 'grains', 'pasta': 'grains', 'oats': 'grains'
}}

def load_json_file(filepath, default=None):
    if default is None:
        default = {}
    try:
        with open(filepath, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json_file(filepath, data):
    with open(filepath, 'w') as file:
        json.dump(data, file)

def load_shopping_list(data: dict):
    if STORAGE == 'json':
        data['shopping_list'] = load_json_file(FILE_PATH, default=[])
    elif STORAGE == 'redis':
        shopping_list = redis_client.get('shopping_list')
        if shopping_list:
            data['shopping_list'] = json.loads(shopping_list)
        else:
            data['shopping_list'] = []

def load_categories(data: dict):
    if STORAGE == 'json':
        data['categories'].update(load_json_file(CATEGORY_FILE, default={}))
    elif STORAGE == 'redis':
        categories = redis_client.get('categories')
        if categories:
            data['categories'].update(json.loads(categories))

def store_shopping_list(data: dict):

    if STORAGE == 'json':
        save_json_file(FILE_PATH, data['shopping_list'])
    elif STORAGE == 'redis':
        redis_client.set('shopping_list', json.dumps(data['shopping_list']))

def store_categories(data: dict):
    if STORAGE == 'json':
        save_json_file(CATEGORY_FILE, data['categories'])
    elif STORAGE == 'redis':
        redis_client.set('categories', json.dumps(data['categories']))
        
load_categories(data)
load_shopping_list(data)

def categorize_items(items):
    categorized = {}
    for item in items:
        category = data['categories'].get(item, 'others')
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(item)
    return categorized


@app.route('/')
def index():
    categorized_items = categorize_items(data['shopping_list'])
    return render_template('index.html', categorized_items=categorized_items,
                           available_categories=list(set(data['categories'].values())))


@app.route('/add', methods=['POST'])
def add_item():
    item = request.form.get('item')
    if item:
        data['shopping_list'].append(item)
        # save_json_file(FILE_PATH, data['shopping_list'])
        store_shopping_list(data)
    return redirect(url_for('index'))


@app.route('/remove', methods=['POST'])
def remove_items():
    checked_items = request.form.getlist('items')
    data['shopping_list'] = [item for item in data['shopping_list'] if item not in checked_items]
    # save_json_file(FILE_PATH, data['shopping_list'])
    store_shopping_list(data)
    return redirect(url_for('index'))


@app.route('/update_category', methods=['POST'])
def update_category():
    item = request.form.get('item')
    category = request.form.get('category')
    if item and category:
        data['categories'][item] = category
        store_categories(data)
        # save_json_file(CATEGORY_FILE, data['categories'])
    return redirect(url_for('index'))


@app.route('/manage_categories', methods=['GET', 'POST'])
def manage_categories():
    if request.method == 'POST':
        action = request.form.get('action')
        category = request.form.get('category')
        item = request.form.get('item')
        if action == 'add_category' and category:
            if category not in data['categories'].values():
                # add something to category
                data['categories']['no item'] = category
        elif action == 'remove_category' and category:
            data['categories'] = {item: c for item, c in data['categories'].items() if c != category}
        elif action == 'add_item' and item and category:
            data['categories'][item] = category
        elif action == 'remove_item' and item:
            data['categories'].pop(item, None)

        # save_json_file(CATEGORY_FILE, data['categories'])
        store_categories(data)

    return render_template('manage_categories.html',
                           categories=set(data['categories'].values()), category_map=data['categories'])


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)