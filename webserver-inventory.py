from flask import Flask, render_template, request, redirect, url_for
import json
import os
import uuid
from datetime import datetime

app = Flask(__name__)
inventory = []

def load_config():
    with open('config.json') as file:
        return json.load(file)

def load_inventory():
    try:
        with open('inventory.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_inventory():
    global inventory
    with open('inventory.json', 'w') as file:
        json.dump(inventory, file, indent=4)

def generate_unique_filename(filename):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    unique_id = str(uuid.uuid4().hex)
    _, extension = os.path.splitext(filename)
    unique_filename = f'{timestamp}_{unique_id}{extension}'
    return unique_filename

@app.route('/')
def index():
    global inventory
    inventory = load_inventory()
    return render_template('index.html', inventory=inventory)

@app.route('/add', methods=['GET', 'POST'])
def add_item():
    global inventory
    if request.method == 'POST':
        item_name = request.form['item_name']
        quantity = int(request.form['quantity'])
        link = request.form['link']
        picture = request.files['picture']
        form_tags = request.form.getlist('tags[]')
        selected_tags = []
        tags = load_config()["tags"]
        for item in form_tags:
            for tag in tags:
                if tag['name'] == item:
                    selected_tags.append(tag)


        if picture.filename:
            unique_filename = generate_unique_filename(picture.filename)
            picture.save('static/' + unique_filename)
        else:
            unique_filename = None
        inventory = load_inventory()
        inventory.append({'item_name': item_name, 'quantity': quantity, 'link': link, 'picture': unique_filename, 'tags': selected_tags})
        save_inventory()
        return redirect(url_for('index'))
    return render_template('add.html', tags = load_config()["tags"])

@app.route('/adjust/<item_name>', methods=['GET', 'POST'])
def adjust_quantity(item_name):
    global inventory
    inventory = load_inventory()
    item = next((item for item in inventory if item['item_name'] == item_name), None)
    if item:
        if request.method == 'POST':
            quantity = int(request.form['quantity'])
            link = request.form['link']
            item['quantity'] = quantity
            item['link'] = link
            print(inventory)
            save_inventory()
            return redirect(url_for('index'))
        return render_template('adjust.html', item=item)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True,host="172.17.26.2")
