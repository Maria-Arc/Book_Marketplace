from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import os

app = Flask(__name__)

def create_db_connection():
    password = "Rocky2014@" 

    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password=password,  # login to root w my password
            database="book_marketplace"
        )
        return connection
    except mysql.connector.Error as err:
        print(f" Database connection failed - {err}")    #if fails print to terminal
        return None


# DB Route
@app.route('/db')
def db_test():
    # Fetch data from database
    connection = create_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, username, address FROM users;")
    result = cursor.fetchall()
    connection.close()
    
    # Pass result to HTML template for formatting
    return render_template('users.html', users=result)

@app.route('/', methods =['GET', 'POST'])
def add():
    if request.method == 'POST':
        user_name = request.form['user_name']  # Getting the user input from the form
        user_pass = request.form['user_pass']  
        
        # You can process or store the input here (e.g., in a database)

        action = request.form['action']

        if action == 'Submit':
            if login(user_name, user_pass):
                print("can login for usern")
                return redirect(url_for('home2', usern= user_name))
                #return f" You have logged in as Username: {user_name} User Pass: {user_pass}"
            else:
                 return f" You cannot log in as Username: {user_name}"   
        else:   
            user_add= request.form['user_add'] 
            if CreateUser(user_name, user_pass, user_add):
                return f" You have created an account as Username: {user_name} User Pass: {user_pass} User Address: {user_add}"
            else:
                return f" You cannot create an account as Username: {user_name}"   

    return render_template('add.html')  # Render the form when visiting the page via GET

#actual homepage once user has logged in
@app.route('/home2', methods = (['GET', 'POST']))
def home2(book = ""):
    #usern = request.args.get('usern', 'Guest')
    usern = request.form.get('usern', request.args.get('usern', 'Guest'))
    result = bookSearch("")
    resultCart = CartSearch(usern)
    connection = create_db_connection()
    cursor = connection.cursor()
    


    carts = CartSearch(usern)
    cursor.execute(" SELECT SUM(Price) FROM cart NATURAL JOIN listing NATURAL JOIN book WHERE username = %s", (usern,))
    price = cursor.fetchone()[0]
    if price is None:
        price = 0
    cursor.execute(" SELECT bio FROM users WHERE username = %s", (usern,))
    bio = cursor.fetchone()[0]
    genre_counts = CartSearchGenreCount()
    

    if request.method == 'POST':
        if request.form["action"] == "delete_account":
            deleteAccount(usern)
            return redirect(url_for('add'))
        elif request.form["action"] == "logout":
             return redirect(url_for('add'))
        elif request.form["action"] == "search_book":
            find_book = request.form['search_book']
            result = bookSearch(find_book)
        elif request.form["action"] == 'sell_book':
            return redirect(url_for('sellbook', usern = usern, carts = resultCart))
        elif request.form["action"] == 'select_book':
            listingid = request.form.get('listing_id')
            connection = create_db_connection()
            cursor = connection.cursor()
            print (usern)
            
            cursor.execute("SELECT 1 FROM users WHERE Username = %s", (usern,))
            if not cursor.fetchone():
                connection.close()
                return render_template('userhome.html', user=usern, books=result, carts = resultCart, price = price, bio = bio, genres=genre_counts) 

            # Now check if that (username, listingid) is already in the cart
            cursor.execute("SELECT 1 FROM cart WHERE Username = %s AND ListingID = %s", (usern, listingid))
            already_in_cart = cursor.fetchone()

            if already_in_cart:
                 carts = CartSearch(usern)
                 genre_counts = CartSearchGenreCount()
                 cursor.execute(" SELECT SUM(Price) FROM cart NATURAL JOIN listing NATURAL JOIN book WHERE username = %s", (usern,))
                 price = cursor.fetchone()[0]
                 cursor.execute(" SELECT bio FROM users WHERE username = %s", (usern,))
                 bio = cursor.fetchone()[0]
                 connection.close()
                 return render_template('userhome.html', user=usern, books=result, carts = resultCart, price = price, bio = bio, genres=genre_counts) 
            else:
                cursor.execute("INSERT INTO cart (username, listingid) VALUES (%s, %s);", (usern, listingid))
                connection.commit()
                connection.close()
                return redirect(url_for('home2', usern=usern,carts = resultCart))

        elif  request.form["action"] == 'remove_cart':
            listingid = request.form.get('listing_id')
            print("listing id is" + listingid)
            RemoveCart(listingid, usern)
            connection.close()
            return redirect(url_for('home2', usern=usern, carts = resultCart))
        elif  request.form["action"] == 'Checkout':
            Checkout(usern)
            result = bookSearch("")
            resultCart = CartSearch(usern)
            connection = create_db_connection()
            cursor = connection.cursor()

            carts = CartSearch(usern)
            genre_counts = CartSearchGenreCount()
            
            cursor.execute(" SELECT SUM(Price) FROM cart NATURAL JOIN listing NATURAL JOIN book WHERE username = %s", (usern,))
            price = cursor.fetchone()[0]
            if price is None:
                price = 0
            connection.close()
            return render_template('userhome.html', user=usern, books=result, carts = resultCart, price = price, bio = bio, genres=genre_counts) 
        elif  request.form["action"] == 'edit_account':
             connection.close()
             return redirect(url_for('edituser', usern = usern))
        elif  request.form["action"] == 'sort_price':
             print("sorting")
             cursor.execute("""
                    SELECT sellerid, Title, author, isbn, genre, price, conditionin, listingid 
                    FROM book 
                    NATURAL JOIN listing 
                    WHERE listingid NOT IN (SELECT ListingID FROM sold)
                    ORDER BY (retailPrice - price) DESC;
                """)
             result = cursor.fetchall()
 
    
    connection.close()
    return render_template('userhome.html', user=usern, books=result, carts = resultCart, price = price, bio = bio, genres=genre_counts)   



def RemoveCart(listingid, usern):
    connection = create_db_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM cart WHERE username = %s AND listingid = %s", (usern, listingid))
    connection.commit()
    connection.close()


def Checkout(usern):
    connection = create_db_connection()
    cursor = connection.cursor()


    carts = CartSearch(usern)
    cursor.execute(" SELECT SUM(Price) FROM cart NATURAL JOIN listing NATURAL JOIN book WHERE username = %s", (usern,))
    price = cursor.fetchone()[0]
    if price is None:
        price = 0

    cursor.execute("SELECT COUNT(*) FROM cart WHERE username = %s;", (usern,))
    numberBooks = cursor.fetchone()[0]

    print("adding into sold:")
    for cart in carts:
        print("listing id  usern")
        print(cart[7] , usern)
        cursor.execute("INSERT INTO sold (ListingID, BuyerId ) VALUES (%s, %s);", (cart[7], usern))
        cursor.execute("DELETE FROM cart WHERE username = %s AND listingId = %s", (usern, cart[7]))
    connection.commit()
    connection.close()
    return render_template( 'userhome.html', user=usern, carts = carts, price = price, num = numberBooks)


def bookSearch(bName):
    connection = create_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT sellerid, Title, author, isbn, genre, price, conditionin, listingid FROM book NATURAL JOIN listing WHERE Title LIKE %s  AND listingid NOT IN (SELECT ListingID FROM sold);", (f"{bName}%",))
    result = cursor.fetchall()
    connection.close()
    return result

def CartSearch(uName):
    connection = create_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT sellerid, Title, author, isbn, genre, price, conditionin, listingid FROM cart NATURAL JOIN listing NATURAL JOIN book WHERE Username = %s;", (uName,))
    result = cursor.fetchall()
    connection.close()
    return result


def CartSearchGenreCount():
    connection = create_db_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT genre, COUNT(*) as count
        FROM listing 
        NATURAL JOIN book
        WHERE listingid NOT IN (SELECT listingid FROM sold)
        GROUP BY genre;
    """)
    result = cursor.fetchall()
    connection.close()
    return result  




def deleteAccount(usern):
    connection = create_db_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM listing WHERE sellerid = %s ", (usern,))
    cursor.execute("DELETE FROM users WHERE username = %s ", (usern,))
    connection.commit()
    connection.close()

def login(usern, userp):
    # Fetch data from database
    connection = create_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT username, password FROM users WHERE username = %s AND password = %s;", (usern, userp))
    result = cursor.fetchone()
    print ("this profile does exist:")
    print (result)
    connection.close()
    
    # Pass result to HTML template for formatting
    if result:
        return True;
    else: 
        return False;

def CreateUser(usern, userp, user_add):
    # Fetch data from database
    connection = create_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT username FROM users WHERE username = %s;", (usern,))
    result = cursor.fetchone()

    
    # Pass result to HTML template for formatting
    if result or len(usern) > 30 or len(userp) > 50 or len(user_add) > 150:
        connection.close()
        return False;  #User alr exists
    else:               #User DNE, make new one
        cursor.execute("INSERT INTO users (username, password, address) VALUES (%s, %s, %s);", (usern, userp, user_add))
        connection.commit()
        connection.close()
        return True;
 
@app.route('/addbook', methods=['GET', 'POST'])
def sellbook():
    usern = request.form.get('usern') or request.args.get('usern', 'Guest')

    connection = create_db_connection()
    cursor = connection.cursor()
    

    if request.method == 'POST':
        if request.form["action"] == "addBook":
            bname = request.form['book_title']
            cond = request.form['book_condition']
            price = request.form['book_price']
            
            cursor.execute("SELECT productnumber FROM book WHERE Title = %s;", (bname,))
            result = cursor.fetchone()
            trash = cursor.fetchall()
            print ("product number is ")
            print( result[0])

            if result:
                productnumber = result[0]
                cursor.execute("INSERT INTO Listing (Price, ConditionIn, SellerId, productnumber) VALUES (%s, %s, %s, %s);", 
                            (price, cond, usern, productnumber))
 
        elif request.form["action"] == "Remove":

                listingid = request.form.get('listing_id')
                cursor.execute("DELETE FROM listing WHERE sellerID = %s AND listingid = %s", (usern, listingid))
                connection.commit()
    




    cursor.execute("SELECT Title, author, price, conditionin, isbn, genre, listingID FROM book NATURAL JOIN listing WHERE SellerId = %s AND listingID NOT IN (SELECT listingid FROM sold);", (usern,))
    result = cursor.fetchall()
    connection.commit()
    connection.close()
    return render_template('sellbook.html', user=usern, books = result)

    

@app.route('/userprofile', methods=['GET', 'POST'])
def edituser():
    usern = request.form.get('usern', request.args.get('usern', 'Guest'))
    connection = create_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT username, bio, address, password FROM users WHERE username = %s;", (usern,))
    result = cursor.fetchall()
    print (result)
    username, bio, address, password = result[0]
    if request.method == 'POST':
        if request.form["action"] == "update_profile":
            passw = request.form['password']
            address = request.form['address']
            bio = request.form['bio']
            connection = create_db_connection()
            cursor = connection.cursor()
            
            cursor.execute(""" UPDATE users SET bio = %s, address = %s, password = %s WHERE username = %s; """, (bio, address, passw, usern))
            connection.commit()
            connection.close()

            return redirect(url_for('edituser', usern=usern))


    return render_template('userprofile.html', user=username, bio=bio, address=address, password=password)



if __name__ == '__main__':
    app.run(debug=True)