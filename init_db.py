
import mysql.connector
from werkzeug.security import generate_password_hash
from config import Config

db = mysql.connector.connect(
    host=Config.MYSQL_HOST,
    user=Config.MYSQL_USER,
    password=Config.MYSQL_PASSWORD,
    database=Config.MYSQL_DATABASE
)

cur = db.cursor()

games = [
    ("Valorant", "FPS", "PC", "Tactical team shooter."),
    ("Counter-Strike 2", "FPS", "PC", "Competitive shooter."),
    ("Minecraft", "Sandbox", "PC", "Build and explore."),
    ("Fortnite", "Battle Royale", "PC", "Multiplayer battle royale."),
    ("EA Sports FC", "Sports", "PlayStation", "Football game."),
    ("Forza Horizon 5", "Racing", "Xbox", "Open-world racing.")
]

for game in games:
    cur.execute("""
        INSERT IGNORE INTO games
        (name, genre, platform, description)
        VALUES (%s, %s, %s, %s)
    """, game)

stations = [
    ("PC-01", "PC", 100),
    ("PC-02", "PC", 100),
    ("PS-01", "PlayStation", 150),
    ("XB-01", "Xbox", 150)
]

for station in stations:
    cur.execute("""
        INSERT IGNORE INTO stations
        (name, station_type, hourly_rate)
        VALUES (%s, %s, %s)
    """, station)

cur.execute("""
    INSERT IGNORE INTO users
    (name, email, password_hash, role)
    VALUES (%s, %s, %s, 'admin')
""", (
    "Administrator",
    "admin@gamingzone.local",
    generate_password_hash("ChangeMe@123")
))

cur.execute("""
    INSERT IGNORE INTO station_games (station_id, game_id)
    SELECT s.id, g.id
    FROM stations s
    CROSS JOIN games g
    WHERE s.station_type = g.platform
""")

db.commit()
cur.close()
db.close()

print("Sample games and stations created.")
print("Admin email: admin@gamingzone.local")
print("Initial password: ChangeMe@123")
print("Change the admin password before using the system.")
