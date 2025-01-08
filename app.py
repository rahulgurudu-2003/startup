from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import razorpay
from datetime import datetime
razorpay_client = razorpay.Client(auth=("rzp_test_nKMhhbSQoripGE", "VT8EU3XT7FlL9irQeAbzchPx"))
app = Flask(__name__)
app.secret_key = '12345678'

db=os.environ['RDS_DB_NAME']
user=os.environ['RDS_USERNAME']
password=os.environ['RDS_PASSWORD']
host=os.environ['RDS_HOSTNAME']
port=os.environ['RDS_PORT']
with mysql.connector.connect(host='host',user='user',password='password',db='db'):
cursor=mydb.cursor(buffered=True)

cursor.execute("CREATE TABLE  if not exits `cart` (`id` int NOT NULL AUTO_INCREMENT,`user` varchar(255) NOT NULL,`itemid` varchar(255) NOT NULL,`name` varchar(255) NOT NULL,`price` int DEFAULT NULL,`image_url` text,PRIMARY KEY (`id`),KEY `user` (`user`),CONSTRAINT `cart_ibfk_1` FOREIGN KEY (`user`) REFERENCES `users` (`name`) ON DELETE CASCADE))")

# def get_db_connection():
#     conn = mysql.connector.connect(
#         host='localhost',  
#         user='root',  
#         password='root', 
#         database='startup'  
#     )
#     return conn


@app.route('/')
def base():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name, image_url, price FROM products LIMIT 6")
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('homepage.html',products=products)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE name = %s', (name,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user'] = user['name']
            return redirect(url_for('homepage1'))
        else:
            return "Invalid credentials, or user does not exist. Please register."
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (name, email, password) VALUES (%s, %s, %s)', (name, email, password))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/homepage')
def homepage():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM wishlist WHERE user = %s', (session['user'],))
    wishlist = cursor.fetchall()
    conn.close()
    session['wishlist'] = {item['itemid']: (item['name'], item['price']) for item in wishlist}
    return render_template('homepage.html', name=session['user'])

@app.route('/homepage1')
def homepage1():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM wishlist WHERE user = %s', (session['user'],))
    wishlist = cursor.fetchall()
    conn.close()
    session['wishlist'] = {item['itemid']: (item['name'], item['price']) for item in wishlist}
    return render_template('homepage1.html', name=session['user'])

@app.route('/product/<product_name>')
def product_detail(product_name):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = %s", (product_name,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()

    if product:
        template_name = f"{product_name.lower()}.html"
        return render_template(template_name, product=product)
    else:
        return "Product not found", 404



@app.route('/wishlist')
def wishlist():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM wishlist WHERE user = %s', (session['user'],))
    wishlist = cursor.fetchall()
    conn.close()
    wishlist_dict = {
        item['itemid']: (item['name'], item['price'], item['image_url'])
        for item in wishlist
    }
    
    return render_template('wishlist.html', wishlist=wishlist_dict)



@app.route('/add_to_wishlist/<itemid>')
def add_to_wishlist(itemid):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT name, price, image_url FROM products WHERE id = %s', (itemid,))
    product = cursor.fetchone()
    conn.close()
    if not product:
        return "Product not found", 404
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT IGNORE INTO wishlist (user, itemid, name, price, image_url) VALUES (%s, %s, %s, %s, %s)',
        (session['user'], itemid, product['name'], product['price'], product['image_url'])
    )
    conn.commit()
    conn.close()
    
    return redirect(request.referrer or url_for('homepage'))


@app.route('/remove_from_wishlist/<itemid>')
def remove_from_wishlist(itemid):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM wishlist WHERE user = %s AND itemid = %s', (session['user'], itemid))
    conn.commit()
    conn.close()
    
    return redirect(url_for('wishlist'))


@app.route('/cart')
def cart():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM cart WHERE user = %s', (session['user'],))
    cart_items = cursor.fetchall()
    conn.close()
    cart_dict = {
        item['itemid']: (item['name'], item['price'], item['image_url']) 
        for item in cart_items
    }
    
    return render_template('cart.html', cart=cart_dict)


@app.route('/add_to_cart/<itemid>')
def add_to_cart(itemid):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT name, price, image_url FROM products WHERE id = %s', (itemid,))
    product = cursor.fetchone()
    conn.close()

    if not product:
        return "Product not found", 404
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT IGNORE INTO cart (user, itemid, name, price, image_url) VALUES (%s, %s, %s, %s, %s)',
        (session['user'], itemid, product['name'], product['price'], product['image_url'])
    )
    conn.commit()
    conn.close()

    return redirect(request.referrer or url_for('homepage'))



@app.route('/remove_from_cart/<itemid>')
def remove_from_cart(itemid):
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cart WHERE user = %s AND itemid = %s', (session['user'], itemid))
    conn.commit()
    conn.close()
    return redirect(url_for('cart'))

@app.route('/pay', methods=['GET'])
def pay():
    if 'user' not in session:
        return redirect(url_for('login'))

    itemid = request.args.get('itemid')
    name = request.args.get('name')
    price = request.args.get('price')

    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT image_url FROM products WHERE id = %s', (itemid,))
    product = cursor.fetchone()
    conn.close()

    image_url = product['image_url'] if product else None

    amount = int(price) * 100
    order = razorpay_client.order.create(dict(
        amount=amount,
        currency="INR",
        payment_capture='1'
    ))
    order_id = order['id']

    return render_template('payment.html', name=name, price=price, order_id=order_id, itemid=itemid, image_url=image_url)




@app.route('/success', methods=['POST'])
def success():
    if 'user' not in session:
        return redirect(url_for('login'))

    payment_id = request.form['razorpay_payment_id']
    order_id = request.form['razorpay_order_id']
    signature = request.form['razorpay_signature']
    image_url = request.form['image_url']


    params = {
        'razorpay_order_id': order_id,
        'razorpay_payment_id': payment_id,
        'razorpay_signature': signature
    }

    try:
        razorpay_client.utility.verify_payment_signature(params)
        item_name = request.form['name']
        item_price = request.form['total_price']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO orders (user, item_name, price, image_url) VALUES (%s, %s, %s, %s)',
               (session['user'], item_name, item_price, image_url))
        conn.commit()
        conn.close()

        return redirect(url_for('orders'))  

    except razorpay.errors.SignatureVerificationError:
        return "Payment verification failed. Please try again.", 400




@app.route('/orders')
def orders():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM orders WHERE user = %s', (session['user'],))
    data = cursor.fetchall()
    conn.close()
    return render_template('orders.html', data=data)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')
    
    if query:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products WHERE name REGEXP %s", (r'\b' + query + r'\b',))
        products = cursor.fetchall()
        conn.close()
    else:
        products = []
    
    for product in products:
        discount = product['discount']
        final_price = product['price'] * (1 - discount / 100)
        product['final_price'] = round(final_price, 2) 

    return render_template('search.html', query=query, products=products)



@app.route('/contact')
def contact_us():
    return render_template('contact.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('homepage'))

@app.route('/review/<int:order_id>')
def review_page(order_id):
    return render_template('review.html', order_id=order_id)

@app.route('/thank-you')
def thank_you():
    return render_template('thank_you.html')

@app.route('/shoes')
def shoes():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Shoes'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('shoes.html', product=product)

@app.route('/watch')
def watch():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Watch'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('watch.html', product=product)

@app.route('/laptop')
def laptop():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Laptop'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('laptop.html', product=product)

@app.route('/iphone')
def iphone():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Iphone'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('iphone.html', product=product)

@app.route('/food')
def food():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Food Items'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('food items.html', product=product)

@app.route('/camera')
def camera():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Camera'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('camera.html', product=product)

@app.route('/washing')
def washing():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Washing Machine'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('washing machine.html', product=product)

@app.route('/ac')
def ac():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Ac Machine'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('ac machine.html', product=product)

@app.route('/music')
def music():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Musical KeyBoards'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('musical keyboards.html', product=product)

@app.route('/neem')
def neem():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Neem Plants'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('neem plants.html', product=product)

@app.route('/kettle')
def kettle():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Electric Kettles'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('electric kettles.html', product=product)

@app.route('/bulb')
def bulb():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Electric Bulbs'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('electric bulbs.html', product=product)

@app.route('/heater')
def heater():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Water heater'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('water heater.html', product=product)

@app.route('/sports')
def sports():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Sports'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('sports.html', product=product)

@app.route('/bag')
def bag():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Bags'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('bags.html', product=product)

@app.route('/sofa')
def sofa():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Sofas Set'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('sofas set.html', product=product)

@app.route('/men1') 
def men1():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Mens Dress 1'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('mens dress 1.html', product=product)

@app.route('/men2')  
def men2():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Mens Dress 2'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('mens dress 2.html', product=product)

@app.route('/men3')  
def men3():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Mens Dress 3'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('mens dress 3.html', product=product)

@app.route('/men4')  
def men4():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Mens Dress 4'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('mens dress 4.html', product=product)

@app.route('/men5') 
def men5():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Mens Dress 5'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('mens dress 5.html', product=product)

@app.route('/men6')
def men6():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Mens Dress 6'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('mens dress 6.html', product=product)

@app.route('/women1') 
def women1():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Womens Dress 1'")  
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('womens dress 1.html', product=product)

@app.route('/women2')  
def women2():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Womens Dress 2'")  
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('womens dress 2.html', product=product)

@app.route('/women3') 
def women3():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Womens Dress 3'")  
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('womens dress 3.html', product=product)

@app.route('/women4')  
def women4():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Womens Dress 4'")  
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('womens dress 4.html', product=product)

@app.route('/women5')
def women5():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Womens Dress 5'")  
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('womens dress 5.html', product=product)

@app.route('/women6') 
def women6():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name = 'Womens Dress 6'")
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('womens dress 6.html', product=product)



if __name__ == '__main__':
    app.run(debug=True)
