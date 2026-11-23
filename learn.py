from flask import Flask, render_template, request, redirect, session
import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
import os
from datetime import datetime, timedelta

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
eng = create_engine("mysql+pymysql://root@localhost:3306/project")
db = scoped_session(sessionmaker(bind=eng))
sara = Flask(__name__)
sara.debug = True
sara.config["SECRET_KEY"] = "randy"

@sara.route("/")
def landing_page():
    try:
        books = db.execute(text("SELECT * FROM books ORDER BY id ASC LIMIT 6")).fetchall()
    except Exception:
        books = []
    return render_template("landing page.html", books=books)

@sara.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        us = request.form.get("user")
        pa = request.form.get("pas")

        if us == "admin" and pa == "admin123":
            session["user"] = us
            session["admin"] = True
            return redirect("/admin")

        result = db.execute(
            text("""
                SELECT username
                FROM login
                WHERE username=:us AND pass_word=:pa
            """),
            {
                "us": us,
                "pa": pa
            }
        ).fetchone()

        if result:
            session["user"] = us
            session["admin"] = False
            return redirect("/home")
        else:
            return render_template(
                "login.html",
                error="Username or Password is incorrect"
            )

    return render_template("login.html")

@sara.route("/home")
def home():
    res = db.execute(
        text("SELECT * FROM books ORDER BY id DESC")
    ).fetchall()

    return render_template(
        "home.html",
        res=res
    )

@sara.route("/admin")
def admin():
    if session.get("admin") != True:
        return redirect("/home")
    return render_template("admin.html")

@sara.route("/addbook", methods=["GET", "POST"])
def addbook():
    if session.get("admin") != True:
        return redirect("/home")

    book_id = request.args.get("id")

    # Fetch liked books for customer liked section in admin
    try:
        liked_books = db.execute(text("""
            SELECT likes.id AS like_id, books.book_name, books.author, books.price, books.image_name, login.username
            FROM likes
            JOIN books ON likes.book_id = books.id
            JOIN login ON likes.user_id = login.id
            ORDER BY likes.id DESC
        """)).fetchall()
    except Exception:
        liked_books = []

    # =========================
    # EDIT BOOK
    # =========================
    if book_id:
        if request.method == "POST":
            book_name = request.form.get("book_name")
            author = request.form.get("author")
            price = request.form.get("price")
            stock = request.form.get("stock")
            description = request.form.get("description")
            image = request.files.get("img")

            if image and image.filename:
                image_name = image.filename
                image.save(os.path.join(APP_ROOT, "static", "photos", image_name))
                db.execute(text("""
                    UPDATE books
                    SET book_name=:book_name,
                        author=:author,
                        price=:price,
                        stock=:stock,
                        description=:description,
                        image_name=:image_name
                    WHERE id=:id
                """), {
                    "book_name": book_name,
                    "author": author,
                    "price": price,
                    "stock": stock,
                    "description": description,
                    "image_name": image_name,
                    "id": book_id
                })
            else:
                db.execute(text("""
                    UPDATE books
                    SET book_name=:book_name,
                        author=:author,
                        price=:price,
                        stock=:stock,
                        description=:description
                    WHERE id=:id
                """), {
                    "book_name": book_name,
                    "author": author,
                    "price": price,
                    "stock": stock,
                    "description": description,
                    "id": book_id
                })

            db.commit()
            return redirect("/viewproducts")

        book = db.execute(text("""
            SELECT *
            FROM books
            WHERE id=:id
        """), {
            "id": book_id
        }).fetchone()

        return render_template(
            "addbooks.html",
            book=book,
            edit=True,
            liked_books=liked_books
        )

    # =========================
    # ADD NEW BOOK
    # =========================
    if request.method == "POST":
        book_name = request.form.get("book_name")
        author = request.form.get("author")
        price = request.form.get("price")
        stock = request.form.get("stock")
        description = request.form.get("description")

        image = request.files.get("img")
        image_name = None

        if image and image.filename:
            image_name = image.filename
            image.save(
                os.path.join(
                    APP_ROOT,
                    "static",
                    "photos",
                    image_name
                )
            )

        db.execute(text("""
            INSERT INTO books
            (book_name, author, price, stock, description, image_name)
            VALUES
            (:book_name, :author, :price, :stock, :description, :image_name)
        """), {
            "book_name": book_name,
            "author": author,
            "price": price,
            "stock": stock,
            "description": description,
            "image_name": image_name
        })

        db.commit()
        return redirect("/viewproducts")

    return render_template(
        "addbooks.html",
        book=None,
        edit=False,
        liked_books=liked_books
    )

@sara.route("/admin/deleteorder/<int:id>", methods=["POST"])
def delete_order(id):
    if session.get("admin") != True:
        return redirect("/home")
    db.execute(text("DELETE FROM payments WHERE id=:id"), {"id": id})
    db.commit()
    return redirect("/admin/orders")

@sara.route("/admin/deletelike/<int:id>", methods=["POST"])
def admin_delete_like(id):
    if session.get("admin") != True:
        return redirect("/home")
    db.execute(
        text("""
            DELETE FROM likes
            WHERE id=:id
        """),
        {
            "id": id
        }
    )
    db.commit()
    return redirect("/addbook")

@sara.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        us = request.form.get("user")
        pa = request.form.get("pas")
        gen = request.form.get("choice")
        mo = request.form.get("mob")
        em = request.form.get("ema")
        db.execute(text("""
            INSERT INTO login(username, pass_word, gender, mobile_number, email)
            VALUES(:us, :pa, :gen, :mo, :em)
        """), {"us": us, "pa": pa, "gen": gen, "mo": mo, "em": em})
        db.commit()
        return redirect("/login")
    return render_template("register.html")

@sara.route("/logout")
def log():
    session.pop("user", None)
    session.pop("admin", None)
    return redirect("/login")

@sara.route("/deletebook/<int:id>", methods=["POST"])
def deletebook(id):
    if session.get("admin") != True:
        return redirect("/home")

    db.execute(
        text("DELETE FROM books WHERE id=:id"),
        {"id": id}
    )
    db.commit()
    return redirect("/viewproducts")

@sara.route("/order/<int:id>", methods=["POST", "GET"])
def order(id):
    if not session.get("user"):
        return redirect("/login")

    book = db.execute(
        text("""
            SELECT *
            FROM books
            WHERE id=:id
        """),
        {"id": id}
    ).fetchone()

    if not book:
        return redirect("/home")

    user = db.execute(
        text("""
            SELECT id
            FROM login
            WHERE username=:username
        """),
        {"username": session["user"]}
    ).fetchone()

    address = db.execute(
        text("""
            SELECT *
            FROM addresses
            WHERE user_id=:user_id
            ORDER BY is_default DESC, id DESC
        """),
        {"user_id": user.id}
    ).fetchall()

    discount_price = float(book.price) * 0.30
    return render_template(
        "order.html",
        book=book,
        address=address,
        discount_price=discount_price
    )

@sara.route("/addresses", methods=["GET", "POST"])
def add_address():
    if not session.get("user"):
        return redirect("/login")

    book_id = request.args.get("book_id") or request.form.get("book_id")

    if request.method == "POST":
        user = db.execute(
            text("""
                SELECT id
                FROM login
                WHERE username=:username
            """),
            {"username": session["user"]}
        ).fetchone()

        nam = request.form.get("nam")
        mob = request.form.get("mob")
        add = request.form.get("addr")
        cit = request.form.get("cit")
        sta = request.form.get("sta")
        pin = request.form.get("pin")
        address_type = request.form.get("address_type")

        db.execute(
            text("""
                INSERT INTO addresses
                (user_id, full_name, mobile, address, city, state, pincode, address_type)
                VALUES
                (:user_id, :nam, :mob, :addr, :cit, :sta, :pin, :address_type)
            """),
            {
                "user_id": user.id,
                "nam": nam,
                "mob": mob,
                "addr": add,
                "cit": cit,
                "sta": sta,
                "pin": pin,
                "address_type": address_type
            }
        )
        db.commit()

        if book_id:
            return redirect("/order/" + str(book_id))
        return redirect("/home")

    return render_template(
        "addresses.html",
        address=None,
        book_id=book_id
    )

@sara.route("/addresses/edit/<int:id>", methods=["GET", "POST"])
def edit_address(id):
    if not session.get("user"):
        return redirect("/login")

    book_id = request.args.get("book_id")

    if request.method == "POST":
        nam = request.form.get("nam")
        mob = request.form.get("mob")
        add = request.form.get("addr")
        cit = request.form.get("cit")
        sta = request.form.get("sta")
        pin = request.form.get("pin")
        address_type = request.form.get("address_type")

        db.execute(
            text("""
                UPDATE addresses
                SET
                    full_name=:nam,
                    mobile=:mob,
                    address=:addr,
                    city=:cit,
                    state=:sta,
                    pincode=:pin,
                    address_type=:address_type
                WHERE id=:id
            """),
            {
                "nam": nam,
                "mob": mob,
                "addr": add,
                "cit": cit,
                "sta": sta,
                "pin": pin,
                "address_type": address_type,
                "id": id
            }
        )
        db.commit()

        if book_id:
            return redirect("/order/" + str(book_id))
        return redirect("/home")

    address = db.execute(
        text("""
            SELECT *
            FROM addresses
            WHERE id=:id
        """),
        {"id": id}
    ).fetchone()

    return render_template(
        "addresses.html",
        address=address,
        book_id=book_id
    )

@sara.route("/addresses/<int:id>", methods=["POST"])
def deleteaddresses(id):
    if not session.get("user"):
        return redirect("/login")

    book_id = request.form.get("book_id")

    db.execute(
        text("DELETE FROM addresses WHERE id=:id"),
        {"id": id}
    )
    db.commit()

    if book_id:
        return redirect("/order/" + str(book_id))
    return redirect("/home")

@sara.route("/payment", methods=["POST"])
def payment():
    if not session.get("user"):
        return redirect("/login")

    book_id = request.form.get("book_id")
    address_id = request.form.get("address_id")
    payment_method = request.form.get("payment")
    quantity = int(request.form.get("quantity", 1))

    user = db.execute(
        text("""
            SELECT id
            FROM login
            WHERE username=:username
        """),
        {"username": session["user"]}
    ).fetchone()

    book = db.execute(
        text("""
            SELECT price
            FROM books
            WHERE id=:id
        """),
        {"id": book_id}
    ).fetchone()

    if not user or not book:
        return redirect("/home")

    original_total = float(book.price) * quantity
    discount_amount = original_total * 70 / 100
    total = original_total - discount_amount
    delivery_date = datetime.now().date() + timedelta(days=5)

    db.execute(
        text("""
            UPDATE books
            SET stock = stock - :quantity
            WHERE id = :book_id
            AND stock >= :quantity
        """),
        {
            "quantity": quantity,
            "book_id": book_id
        }
    )

    db.execute(
        text("""
            INSERT INTO payments
            (
                user_id,
                book_id,
                address_id,
                payment_method,
                original_amount,
                discount_amount,
                amount,
                quantity,
                delivery_date
            )
            VALUES
            (
                :user_id,
                :book_id,
                :address_id,
                :payment_method,
                :original_amount,
                :discount_amount,
                :amount,
                :quantity,
                :delivery_date
            )
        """),
        {
            "user_id": user.id,
            "book_id": book_id,
            "address_id": address_id,
            "payment_method": payment_method,
            "original_amount": original_total,
            "discount_amount": discount_amount,
            "amount": total,
            "quantity": quantity,
            "delivery_date": delivery_date
        }
    )
    db.commit()

    return redirect("/payment/" + str(book_id))

@sara.route("/payment/<int:id>")
def payment_page(id):
    if not session.get("user"):
        return redirect("/login")

    book = db.execute(
        text("""
            SELECT *
            FROM books
            WHERE id=:id
        """),
        {"id": id}
    ).fetchone()

    payment = db.execute(
        text("""
            SELECT *
            FROM payments
            WHERE book_id=:book_id
            AND user_id=(
                SELECT id
                FROM login
                WHERE username=:username
            )
            ORDER BY id DESC
            LIMIT 1
        """),
        {
            "book_id": id,
            "username": session["user"]
        }
    ).fetchone()

    return render_template(
        "payment.html",
        book=book,
        payment=payment
    )

@sara.route("/vieworders")
def vieworders():
    if not session.get("user"):
        return redirect("/login")
    return redirect("/orderpage")

@sara.route("/orderpage")
def orderpage():
    if not session.get("user"):
        return redirect("/login")

    orders = db.execute(
        text("""
            SELECT
                p.id AS order_id,
                b.book_name,
                b.image_name,
                b.author,
                p.quantity,
                p.amount,
                p.payment_method,
                p.payment_status,
                p.created_at,
                p.delivery_date
            FROM payments p
            JOIN books b
                ON p.book_id = b.id
            WHERE p.user_id = (
                SELECT id
                FROM login
                WHERE username=:username
            )
            ORDER BY p.id DESC
        """),
        {
            "username": session["user"]
        }
    ).fetchall()

    return render_template(
        "orderpage.html",
        orders=orders
    )

@sara.route("/cancelorder/<int:id>", methods=["POST"])
def cancelorder(id):
    if not session.get("user"):
        return redirect("/login")

    db.execute(
        text("""
            UPDATE payments
            SET payment_status='Cancelled'
            WHERE id=:id
            AND user_id=(
                SELECT id
                FROM login
                WHERE username=:username
            )
        """),
        {
            "id": id,
            "username": session["user"]
        }
    )
    db.commit()
    return redirect("/orderpage")

@sara.route("/like/<int:id>", methods=["POST"])
def like(id):
    if not session.get("user"):
        return redirect("/login")

    user = db.execute(
        text("""
            SELECT id
            FROM login
            WHERE username=:username
        """),
        {"username": session["user"]}
    ).fetchone()

    check = db.execute(
        text("""
            SELECT id
            FROM likes
            WHERE user_id=:user_id
            AND book_id=:book_id
        """),
        {
            "user_id": user.id,
            "book_id": id
        }
    ).fetchone()

    if not check:
        db.execute(
            text("""
                INSERT INTO likes
                (user_id, book_id)
                VALUES
                (:user_id, :book_id)
            """),
            {
                "user_id": user.id,
                "book_id": id
            }
        )
        db.commit()

    return redirect("/home")

@sara.route("/productoverview")
def productoverview():
    if not session.get("user"):
        return redirect("/login")

    user = db.execute(
        text("""
            SELECT id
            FROM login
            WHERE username=:username
        """),
        {"username": session["user"]}
    ).fetchone()

    books = db.execute(
        text("""
            SELECT books.*
            FROM books
            INNER JOIN likes
            ON books.id = likes.book_id
            WHERE likes.user_id=:user_id
            ORDER BY likes.id DESC
        """),
        {"user_id": user.id}
    ).fetchall()

    return render_template(
        "productoverview.html",
        books=books
    )

@sara.route("/admin/orders")
def admin_orders():
    if session.get("admin") != True:
        return redirect("/home")

    orders = db.execute(
        text("""
            SELECT
                p.id,
                p.book_id,
                p.address_id,
                p.payment_method,
                p.amount,
                p.payment_status,
                p.quantity,
                p.delivery_date,
                p.created_at
            FROM payments p
            ORDER BY p.id DESC
        """)
    ).fetchall()

    return render_template(
        "order management.html",
        orders=orders
    )

@sara.route("/viewusers")
def viewusers():
    if session.get("admin") != True:
        return redirect("/home")

    users = db.execute(
        text("""
            SELECT
                id,
                username,
                gender,
                mobile_number,
                email
            FROM login
            WHERE username != 'admin'
            ORDER BY id DESC
        """)
    ).fetchall()

    return render_template(
        "view user.html",
        users=users
    )

@sara.route("/viewproducts")
def viewproducts():
    if session.get("admin") != True:
        return redirect("/home")

    books = db.execute(
        text("""
            SELECT *
            FROM books
            ORDER BY id DESC
        """)
    ).fetchall()

    return render_template(
        "view products.html",
        books=books
    )

if __name__ == "__main__":
    sara.run(port=5555)
