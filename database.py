import aiosqlite

DB_NAME = "cafe.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                time TEXT,
                guests INTEGER,
                status TEXT DEFAULT 'new'
            )
        """)
        await db.commit()

async def save_booking(user_id, name, time, guests):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO bookings (user_id, name, time, guests) VALUES (?, ?, ?, ?)",
            (user_id, name, time, guests)
        )
        await db.commit()

async def get_user_bookings(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id, time, guests FROM bookings WHERE user_id = ? AND status = 'new' ORDER BY id DESC",
            (user_id,)
        )
        return await cursor.fetchall()

async def cancel_booking(booking_id, user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE id = ? AND user_id = ?",
            (booking_id, user_id)
        )
        await db.commit()

async def get_all_active_bookings():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id, name, time, guests, user_id FROM bookings WHERE status = 'new' ORDER BY id DESC"
        )
        return await cursor.fetchall()
