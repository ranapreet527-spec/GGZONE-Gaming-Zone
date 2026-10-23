
from datetime import datetime
from functools import wraps
from decimal import Decimal

import mysql.connector
from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash, abort
)
from werkzeug.security import (
    generate_password_hash, check_password_hash
)
from config import Config

app = Flask(__name__)
app.config.from_object(Config)


def get_db():
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE
    )


def query(sql, params=(), one=False):
    db = get_db()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        result = cur.fetchone() if one else cur.fetchall()
        return result
    finally:
        cur.close()
        db.close()


def execute(sql, params=()):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(sql, params)
        db.commit()
        return cur.lastrowid
    finally:
        cur.close()
        db.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@app.route("/")
def index():
    # Redirect to login if the user is not logged in
    if not session.get("user_id"):
        return redirect(url_for("login"))

    games = query("""
        SELECT * FROM games
        WHERE active = TRUE
        ORDER BY name
    """)

    stations = query("""
        SELECT * FROM stations
        WHERE status = 'available'
        ORDER BY name
    """)

    return render_template(
        "index.html",
        games=games,
        stations=stations
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 8:
            flash("Enter all details. Password must be at least 8 characters.", "danger")
            return redirect(url_for("register"))

        try:
            execute("""
                INSERT INTO users (name, email, password_hash)
                VALUES (%s, %s, %s)
            """, (
                name, email, generate_password_hash(password)
            ))
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))
        except mysql.connector.IntegrityError:
            flash("That email is already registered.", "danger")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = query(
            "SELECT * FROM users WHERE email = %s",
            (email,), one=True
        )

        if user and check_password_hash(
            user["password_hash"], password
        ):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            return redirect(url_for("admin") if
                            user["role"] == "admin"
                            else url_for("index"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out.", "success")
    return redirect(url_for("index"))


@app.route("/games")
def games():
    items = query("""
        SELECT * FROM games
        WHERE active = TRUE
        ORDER BY name
    """)
    return render_template("games.html", games=items)

@app.route("/stations")
def stations():
    items = query("SELECT * FROM stations ORDER BY name")
    return render_template("stations.html", stations=items)


@app.route("/book", methods=["GET", "POST"])
@login_required
def book():
    games = query("""
        SELECT * FROM games
        WHERE active = TRUE ORDER BY name
    """)
    stations = query("""
        SELECT * FROM stations
        WHERE status = 'available' ORDER BY name
    """)

    if request.method == "POST":
        try:
            station_id = int(request.form["station_id"])
            game_id = int(request.form["game_id"])
            date = request.form["booking_date"]
            start = request.form["start_time"]
            end = request.form["end_time"]

            start_dt = datetime.strptime(
                date + " " + start, "%Y-%m-%d %H:%M"
            )
            end_dt = datetime.strptime(
                date + " " + end, "%Y-%m-%d %H:%M"
            )

            if start_dt <= datetime.now() or end_dt <= start_dt:
                flash("Choose a future time and a valid end time.", "danger")
                return redirect(url_for("book"))

            compatible = query("""
                SELECT s.id
                FROM stations s
                JOIN station_games sg ON sg.station_id = s.id
                JOIN games g ON g.id = sg.game_id
                WHERE s.id = %s AND g.id = %s
                  AND s.status = 'available'
                  AND g.active = TRUE
            """, (station_id, game_id), one=True)

            if not compatible:
                flash("That game is not available on this station.", "danger")
                return redirect(url_for("book"))

            conflict = query("""
                SELECT id FROM bookings
                WHERE station_id = %s
                  AND booking_date = %s
                  AND status IN ('pending', 'approved')
                  AND start_time < %s
                  AND end_time > %s
            """, (station_id, date, end, start), one=True)

            if conflict:
                flash("This station is already booked during that time.", "danger")
                return redirect(url_for("book"))

            execute("""
                INSERT INTO bookings
                (user_id, station_id, game_id, booking_date,
                 start_time, end_time)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                session["user_id"], station_id,
                game_id, date, start, end
            ))

            flash("Booking request submitted for approval.", "success")
            return redirect(url_for("my_bookings"))

        except (ValueError, KeyError):
            flash("Please enter valid booking details.", "danger")

    return render_template(
        "book.html", games=games, stations=stations
    )


@app.route("/my-bookings")
@login_required
def my_bookings():
    bookings = query("""
        SELECT b.*, g.name AS game_name,
               s.name AS station_name, s.hourly_rate,
               bl.amount, bl.payment_status
        FROM bookings b
        JOIN games g ON g.id = b.game_id
        JOIN stations s ON s.id = b.station_id
        LEFT JOIN bills bl ON bl.booking_id = b.id
        WHERE b.user_id = %s
        ORDER BY b.created_at DESC
    """, (session["user_id"],))

    return render_template(
        "my_bookings.html", bookings=bookings
    )


@app.route("/admin")
@login_required
@admin_required
def admin():
    stats = {
        "users": query(
            "SELECT COUNT(*) AS n FROM users", one=True
        )["n"],
        "games": query(
            "SELECT COUNT(*) AS n FROM games", one=True
        )["n"],
        "bookings": query(
            "SELECT COUNT(*) AS n FROM bookings", one=True
        )["n"],
        "revenue": query(
            "SELECT COALESCE(SUM(amount), 0) AS n "
            "FROM bills WHERE payment_status = 'paid'",
            one=True
        )["n"]
    }

    bookings = query("""
        SELECT b.*, u.name AS customer,
               g.name AS game_name, s.name AS station_name
        FROM bookings b
        JOIN users u ON u.id = b.user_id
        JOIN games g ON g.id = b.game_id
        JOIN stations s ON s.id = b.station_id
        ORDER BY b.created_at DESC
    """)

    return render_template(
        "admin.html", stats=stats, bookings=bookings
    )


@app.route("/admin/booking/<int:booking_id>/<action>",
           methods=["POST"])
@login_required
@admin_required
def booking_action(booking_id, action):
    if action not in ("approve", "reject"):
        abort(400)

    booking = query("""
        SELECT * FROM bookings WHERE id = %s
    """, (booking_id,), one=True)

    if not booking or booking["status"] != "pending":
        flash("Booking not found or already processed.", "danger")
        return redirect(url_for("admin"))

    new_status = "approved" if action == "approve" else "rejected"

    if action == "approve":
        conflict = query("""
            SELECT id FROM bookings
            WHERE station_id = %s
              AND booking_date = %s
              AND status = 'approved'
              AND start_time < %s AND end_time > %s
              AND id <> %s
        """, (
            booking["station_id"], booking["booking_date"],
            booking["end_time"], booking["start_time"],
            booking_id
        ), one=True)

        if conflict:
            flash("Cannot approve: another booking overlaps.", "danger")
            return redirect(url_for("admin"))

    execute(
        "UPDATE bookings SET status = %s WHERE id = %s",
        (new_status, booking_id)
    )

    if action == "approve":
        execute("""
            INSERT IGNORE INTO gaming_sessions (booking_id)
            VALUES (%s)
        """, (booking_id,))

    flash("Booking updated.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/games", methods=["GET", "POST"])
@login_required
@admin_required
def manage_games():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        genre = request.form.get("genre", "").strip()
        platform = request.form.get("platform", "")
        description = request.form.get("description", "").strip()

        if not name or not genre or platform not in (
            "PC", "PlayStation", "Xbox"
        ):
            flash("Enter valid game details.", "danger")
        else:
            try:
                execute("""
                    INSERT INTO games
                    (name, genre, platform, description)
                    VALUES (%s, %s, %s, %s)
                """, (name, genre, platform, description))
                flash("Game added.", "success")
            except mysql.connector.IntegrityError:
                flash("A game with that name already exists.", "danger")

        return redirect(url_for("manage_games"))

    items = query("SELECT * FROM games ORDER BY name")
    return render_template("manage_games.html", games=items)


@app.route("/admin/game/<int:game_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_game(game_id):
    execute("""
        UPDATE games SET active = NOT active WHERE id = %s
    """, (game_id,))
    flash("Game status updated.", "success")
    return redirect(url_for("manage_games"))


@app.route("/admin/session/<int:booking_id>/<action>",
           methods=["POST"])
@login_required
@admin_required
def session_action(booking_id, action):
    booking = query("""
        SELECT * FROM bookings WHERE id = %s
    """, (booking_id,), one=True)

    if not booking or booking["status"] != "approved":
        abort(400)

    gaming_session = query("""
        SELECT * FROM gaming_sessions WHERE booking_id = %s
    """, (booking_id,), one=True)

    if not gaming_session:
        abort(400)

    if action == "start" and gaming_session["status"] == "not_started":
        execute("""
            UPDATE gaming_sessions
            SET status = 'running', actual_start = NOW()
            WHERE booking_id = %s
        """, (booking_id,))
        flash("Gaming session started.", "success")

    elif action == "end" and gaming_session["status"] == "running":
        db = get_db()
        cur = db.cursor(dictionary=True)
        try:
            cur.execute("""
                SELECT TIMESTAMPDIFF(
                    SECOND, actual_start, NOW()
                ) AS seconds_used
                FROM gaming_sessions WHERE booking_id = %s
            """, (booking_id,))
            row = cur.fetchone()
            seconds = max(0, row["seconds_used"] or 0)

            cur.execute("""
                UPDATE gaming_sessions
                SET status = 'ended', actual_end = NOW()
                WHERE booking_id = %s
            """, (booking_id,))

            cur.execute("""
                SELECT s.hourly_rate
                FROM bookings b
                JOIN stations s ON s.id = b.station_id
                WHERE b.id = %s
            """, (booking_id,))
            rate = cur.fetchone()["hourly_rate"]

            amount = (
                Decimal(str(rate)) *
                Decimal(seconds) / Decimal(3600)
            ).quantize(Decimal("0.01"))

            cur.execute("""
                INSERT INTO bills (booking_id, amount)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE amount = VALUES(amount)
            """, (booking_id, str(amount)))

            cur.execute("""
                UPDATE bookings SET status = 'completed'
                WHERE id = %s
            """, (booking_id,))

            db.commit()
            flash("Session ended and bill generated.", "success")
        finally:
            cur.close()
            db.close()
    else:
        flash("Invalid session action.", "danger")

    return redirect(url_for("admin"))


@app.route("/admin/bill/<int:booking_id>/pay", methods=["POST"])
@login_required
@admin_required
def mark_paid(booking_id):
    method = request.form.get("payment_method", "Cash")
    if method not in ("Cash", "UPI", "Card"):
        abort(400)

    execute("""
        UPDATE bills
        SET payment_status = 'paid', payment_method = %s
        WHERE booking_id = %s
    """, (method, booking_id))

    flash("Payment status updated.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/reports")
@login_required
@admin_required
def reports():
    revenue = query("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM bills WHERE payment_status = 'paid'
    """, one=True)

    daily = query("""
        SELECT DATE(created_at) AS day,
               SUM(amount) AS revenue
        FROM bills
        WHERE payment_status = 'paid'
        GROUP BY DATE(created_at)
        ORDER BY day DESC
        LIMIT 30
    """)

    return render_template(
        "admin.html",
        stats={
            "users": query("SELECT COUNT(*) AS n FROM users", one=True)["n"],
            "games": query("SELECT COUNT(*) AS n FROM games", one=True)["n"],
            "bookings": query("SELECT COUNT(*) AS n FROM bookings", one=True)["n"],
            "revenue": revenue["total"]
        },
        bookings=[],
        daily=daily
    )


@app.errorhandler(403)
def forbidden(error):
    return "Access denied. Administrator permission required.", 403


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
