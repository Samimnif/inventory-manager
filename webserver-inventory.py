from flask import Flask, render_template, request, redirect, url_for, Response
import json
import os
import uuid
from datetime import datetime
import socket
#import requests
from flask_apscheduler import APScheduler
from functools import wraps
from price_finder import *

url = ""

app = Flask(__name__)
scheduler = APScheduler()
inventory = []
loaner = []
shopping = []

def check_auth(username, password):
    # Replace this with your authentication logic
    # Verify if the provided username and password are valid
    # You can check against a database or any other authentication mechanism
    return username == 'sprott' and password == 'password'

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Unauthorized', 
        401, 
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# Apply the decorator to the routes that require authentication
@app.before_request
@requires_auth
def before_request():
    pass

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

def unreturned_items():
    global loaner
    loaner = load_loan()
    count = 0
    for item in loaner:
        if item['return'] != "done":
            count += 1
    print(count)
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
        if item["return"] != "done" and item["return_date"] <= today:
            if item["return_date"] < today:
                item["return"] = "over"
            else:
                item["return"] = "yes"
            due_list.append(item)
        elif item["return"] != "done" and item["return_date"] > today:
            item["return"] = "no"
    save_loan()
    return due_list

@app.route('/')
def index():
    global inventory, shopping
    inventory = load_inventory()
    shopping = load_shop()
    return render_template('index.html', inventory=inventory, shopItems=unpurchased_items(), loanedItems=unreturned_items(), tags = load_config()["tags"])

@app.route('/about')
def about():
    global inventory, shopping
    inventory = load_inventory()
    shopping = load_shop()
    return render_template('about.html', inventory=inventory, shopItems=unpurchased_items(), tags = load_config()["tags"], tags2 = load_config()["shopping_type"])

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
        unique_id = str(uuid.uuid4().hex)
        print(inventory)
        save_inventory()
        # Save the loan object to loaner.json
        loaner = load_loan()
        loaner.append({"loaner_name": loaner_name, "id": unique_id, "date": datetime.now().strftime('%Y-%m-%d @ %H:%M:%S'), "loaned_item": loaned_item, 'return_date': return_date, "return": "no"})
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

@app.route('/return_loan', methods=['POST'])
def return_loan():
    global loaner, inventory
    loaner = load_loan()
    inventory = load_inventory()
    if request.method == 'POST':
        itemID = request.form['item_id']
        for item in loaner:
            if item['id'] == itemID:
                item['return'] = "done"
                i = next((i for i in inventory if i['item_name'] == item['loaned_item']), None)
                i['quantity'] += 1
                print('done')
                print(item)
                save_loan()
                save_inventory()
                print(loaner)
                break
        return redirect(url_for('loaned_page'))

@app.route('/shopping', methods=['GET', 'POST'])
def shopping():
    global shopping
    shopping = load_shop()
    shoppingM = load_shop()
    for item in shoppingM:
        #if item['purchased'] == 'no':
        #    item['price'] = get_product_price(item['link'])
        item["date"] = datetime.strptime(item["date"], "%Y-%m-%d @ %H:%M:%S")
    shoppingM.sort(key=lambda x: x["date"], reverse=True)

    if request.method == 'POST':
        item = request.form['item']
        customer = request.form['customer']
        unique_id = str(uuid.uuid4().hex)
        link = request.form['link']
        quantity = request.form['quantity']
        selected_tags = []
        form_tags = request.form.getlist('tags2[]')
        tags = load_config()["shopping_type"]
        for i in form_tags:
            for tag in tags:
                if tag['name'] == i:
                    selected_tags.append(tag)
        if 'archive' in request.form:
            shopping.append({'item': item, 'customer': customer, 'link': link, 'quantity': quantity, 'id': unique_id, 'purchased': "archive", 'date': datetime.now().strftime('%Y-%m-%d @ %H:%M:%S'), 'tags': selected_tags, 'price': get_product_price(link)})
        else:
            shopping.append({'item': item, 'customer': customer, 'link': link, 'quantity': quantity, 'id': unique_id, 'purchased': "no", 'date': datetime.now().strftime('%Y-%m-%d @ %H:%M:%S'), 'tags': selected_tags, 'price': get_product_price(link)})
        save_shop()
        return redirect(url_for('shopping'))
    return render_template('shopping.html', shopping_list=shoppingM, tags=load_config()["shopping_type"])

@app.route('/purchase', methods=['POST'])
def purchase():
    global shopping
    shopping = load_shop()
    if request.method == 'POST':
        itemID = request.form['item_id']
        oredrID = request.form['order_id']
        noteItem = request.form['notes_id']
        for item in shopping:
            if item['id'] == itemID:
                item['purchased'] = "yes"
                item['date'] = datetime.now().strftime('%Y-%m-%d @ %H:%M:%S')
                item['order_id'] = oredrID
                item['note'] = noteItem
                save_shop()
                break
        return redirect(url_for('shopping'))

@app.route('/decline_purchase', methods=['POST'])
def decline_purchase():
    global shopping
    shopping = load_shop()
    if request.method == 'POST':
        itemID = request.form['item_id']
        noteItem = request.form['notes_id']
        for item in shopping:
            if item['id'] == itemID:
                item['purchased'] = "declined"
                item['date'] = datetime.now().strftime('%Y-%m-%d @ %H:%M:%S')
                item['note'] = noteItem
                save_shop()
                break
        return redirect(url_for('shopping'))

@app.route('/archive_purchase', methods=['POST'])
def archive_purchase():
    global shopping
    shopping = load_shop()
    if request.method == 'POST':
        itemID = request.form['item_id']
        for item in shopping:
            if item['id'] == itemID:
                item['purchased'] = "archive"
                save_shop()
                break
        return redirect(url_for('shopping'))

@app.route('/edit_shopping', methods=['POST'])
def edit_shopping():
    global shopping
    shopping = load_shop()
    if request.method == 'POST':
        name = request.form['name']
        customer = request.form['customer']
        link = request.form['link']
        quantity = request.form['quantity']
        itemID = request.form['item_id']
        selected_tags = []
        form_tags = request.form.getlist('tags[]')
        tags = load_config()["shopping_type"]
        for i in form_tags:
            for tag in tags:
                if tag['name'] == i:
                    selected_tags.append(tag)
        for item in shopping:
            if item['id'] == itemID:
                item['item'] = name
                item['customer'] = customer
                item['link'] = link
                item['quantity'] = quantity
                item['tags'] = selected_tags
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
                shopping.remove(item)
                save_shop()
                break
    return redirect(url_for('shopping'))

@app.route('/move_shopping', methods=['POST'])
def move_shopping():
    global shopping
    shopping = load_shop()
    if request.method == 'POST':
        itemID = request.form['item_id']
        for item in shopping.copy():
            if item['id'] == itemID:
                item['purchased'] = 'no'
                save_shop()
                break
    return redirect(url_for('shopping'))

def update_loan():
    notify_loan(check_loaners())

if __name__ == '__main__':
    '''hostname=socket.gethostname()   
    IPAddr=socket.gethostbyname(hostname)
    print(IPAddr)'''
    #scheduler.add_job(id='check_loaner', func=update_loan, trigger='interval', hours=24)
    #scheduler.start()
    app.run(debug=True,port=8000)
