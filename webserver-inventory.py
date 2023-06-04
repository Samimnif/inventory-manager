from flask import Flask, render_template, request, redirect, url_for
import json
import os
import uuid
from datetime import datetime
import socket
import requests

url = "https://cmailcarletonca.webhook.office.com/webhookb2/a415d00c-3582-4ea0-bf93-abdfe71fcff7@6ad91895-de06-485e-bc51-fce126cc8530/IncomingWebhook/6e48ee28eff2481ea1f858698987186d/a60094b8-ba28-4db9-a0a0-7a42f06375b6"

app = Flask(__name__)
inventory = []
loaner = []
shopping = []

def save_shop():
    global shopping
    with open('shopping.json', 'w') as file:
        json.dump(shopping, file, indent=4)

def load_shop():
    try:
        with open('shopping.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_loan():
    global loaner
    with open('loaner.json', 'w') as file:
        json.dump(loaner, file, indent=4)

def load_loan():
    try:
        with open('loaner.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

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

def unpurchased_items():
    global shopping
    shopping = load_shop()
    count = 0
    for item in shopping:
        if item['purchased'] == "no":
            count += 1
    return count

def notify_loan(due_list):
    global url
    if (len(due_list) == 0):
        return
    mess = ''
    for item in due_list:
        mess += f'Person\'s Name: {item["loaner_name"]} - Item Loaned: {item["loaned_item"]} - Due on: {item["return_date"]}</pre>'
    mess += "Please contact them for the device return"
    payload = {
        "title": "The following borrowed items are due:",
        "text": mess
    }
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    print(response.text.encode('utf8'))

def check_loaners():
    global loaner
    loaner = load_loan()
    due_list = []
    today = datetime.today().strftime('%Y-%m-%d')
    for item in loaner:
        if item["return_date"] != "done" and item["return_date"] <= today:
            if item["return_date"] < today:
                item["return"] = "over"
            else:
                item["return"] = "yes"
            due_list.append(item)
        elif item["return_date"] > today:
            item["return"] = "no"
    save_loan()
    return due_list

@app.route('/')
def index():
    global inventory, shopping
    inventory = load_inventory()
    shopping = load_shop()
    return render_template('index.html', inventory=inventory, shopItems=unpurchased_items(), tags = load_config()["tags"])

@app.route('/search', methods=['POST'])
def search():
    global inventory
    inventory = load_inventory()

    if request.method == 'POST':
        search_query = request.form['search_bar']
        form_tags = request.form.getlist('tags[]')
        
        selected_tags = []
        tags = load_config()["tags"]
        for item in form_tags:
            for tag in tags:
                if tag['name'] == item:
                    selected_tags.append(tag)
        # Perform search logic
        search_results = []
        for item in inventory:
            if (search_query.lower() in str(item['item_name']).lower() and search_query != "") or all(tag in [tag['name'] for tag in item['tags']] for tag in form_tags):
                search_results.append(item)


        return render_template('search_results.html', search_query=search_query, selected_tags=selected_tags, results=search_results)

    return redirect(url_for('index'))

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
            form_tags = request.form.getlist('tags[]')
            selected_tags = []
            tags = load_config()["tags"]
            for i in form_tags:
                for tag in tags:
                    if tag['name'] == i:
                        selected_tags.append(tag)
            print(selected_tags)
            print(item['tags'])
            item['tags']= selected_tags
            item['quantity'] = quantity
            item['link'] = link
            print(inventory)
            save_inventory()
            return redirect(url_for('index'))
        return render_template('adjust.html', item=item, tags = load_config()["tags"])
    return redirect(url_for('index'))

@app.route('/remove', methods=['GET', 'POST'])
def remove_item():
    global inventory
    inventory = load_inventory()
    if request.method == 'POST':
        selected_items = request.form.getlist('item_checkbox')
        print(selected_items)
        # Remove selected items from inventory
        for item in inventory.copy():
            if item['item_name'] in selected_items:
                print('found')
                inventory.remove(item)
        save_inventory()
        return redirect(url_for('index'))

    return render_template('remove.html', inventory=inventory)

@app.route('/record_loan', methods=['GET', 'POST'])
def record_loan():
    global inventory, loaner
    inventory = load_inventory()
    loaner = load_loan()
    if request.method == 'POST':
        loaner_name = request.form['loaner_name']
        loaned_item = request.form['loaned_item']
        return_date = request.form['date_return']
        item = next((item for item in inventory if item['item_name'] == loaned_item), None)
        item['quantity'] -= 1
        print(inventory)
        save_inventory()
        # Save the loan object to loaner.json
        loaner = load_loan()
        loaner.append({"loaner_name": loaner_name, "date": datetime.now().strftime('%Y-%m-%d @ %H:%M:%S'), "loaned_item": loaned_item, 'return_date': return_date, "return": "no"})
        save_loan()
        return redirect(url_for('index'))

    return render_template('record_loan.html', inventory=inventory)

@app.route('/record_loan/<item_name>')
def record_loan2(item_name):
    global inventory, loaner
    inventory = load_inventory()
    loaner = load_loan()
    print(item_name)
    return render_template('record_loan.html', inventory=inventory, item_option=item_name)

@app.route('/loaned')
def loaned_page():
    global loaner, inventory
    check_loaners()
    inventory = load_inventory()
    loaner = load_loan()
    return render_template('loaned.html', loaned_items=loaner, items=inventory)

@app.route('/shopping', methods=['GET', 'POST'])
def shopping():
    global shopping
    shopping = load_shop()
    if request.method == 'POST':
        item = request.form['item']
        unique_id = str(uuid.uuid4().hex)
        link = request.form['link']
        quantity = request.form['quantity']
        shopping.append({'item': item, 'link': link, 'quantity': quantity, 'id': unique_id, 'purchased': "no"})
        save_shop()
        return redirect(url_for('shopping'))
    return render_template('shopping.html', shopping_list=shopping)

@app.route('/purchase', methods=['POST'])
def purchase():
    global shopping
    shopping = load_shop()
    if request.method == 'POST':
        itemID = request.form['item_id']
        for item in shopping:
            if item['id'] == itemID:
                item['purchased'] = "yes"
                item['date'] = datetime.now().strftime('%Y-%m-%d @ %H:%M:%S')
                save_shop()
                break
        return redirect(url_for('shopping'))

@app.route('/decline_purchase', methods=['POST'])
def decline_purchase():
    global shopping
    shopping = load_shop()
    if request.method == 'POST':
        itemID = request.form['item_id']
        for item in shopping:
            if item['id'] == itemID:
                item['purchased'] = "declined"
                item['date'] = datetime.now().strftime('%Y-%m-%d @ %H:%M:%S')
                save_shop()
                break
        return redirect(url_for('shopping'))

@app.route('/edit_shopping', methods=['POST'])
def edit_shopping():
    global shopping
    shopping = load_shop()
    if request.method == 'POST':
        name = request.form['name']
        link = request.form['link']
        quantity = request.form['quantity']
        itemID = request.form['item_id']
        for item in shopping:
            if item['id'] == itemID:
                item['item'] = name
                item['link'] = link
                item['quantity'] = quantity
                save_shop()
                break
        return redirect(url_for('shopping'))

@app.route('/delete_shopping', methods=['POST'])
def delete_shopping():
    global shopping
    shopping = load_shop()
    if request.method == 'POST':
        itemID = request.form['item_id']
        for item in shopping.copy():
            if item['id'] == itemID:
                print('found')
                shopping.remove(item)
                save_shop()
                break
        return redirect(url_for('shopping'))

if __name__ == '__main__':
    hostname=socket.gethostname()   
    IPAddr=socket.gethostbyname(hostname)
    print(IPAddr)
    app.run(debug=True,host=f"{IPAddr}")
