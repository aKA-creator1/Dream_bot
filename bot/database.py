import aiosqlite

DB_PATH = None


async def init_db():
    from bot.config import DATABASE_PATH
    global DB_PATH
    DB_PATH = DATABASE_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            is_premium INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            description TEXT,
            target_value REAL DEFAULT 100,
            current_value REAL DEFAULT 0,
            unit TEXT DEFAULT '',
            deadline TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            goal_id INTEGER,
            log_date TEXT,
            earned REAL DEFAULT 0,
            note TEXT,
            mood INTEGER DEFAULT 5
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS streaks (
            user_id INTEGER PRIMARY KEY,
            current_streak INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            last_checkin TEXT
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS wishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            wish_text TEXT,
            wish_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS thoughts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            thought_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS promo_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            days INTEGER DEFAULT 7,
            total_uses INTEGER DEFAULT 1,
            used_uses INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        await db.commit()


async def _get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def create_user(user_id, username=None, first_name=None):
    db = await _get_db()
    try:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name)
        )
        await db.commit()
    finally:
        await db.close()


async def get_user(user_id):
    db = await _get_db()
    try:
        rows = await db.execute_fetchall("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return dict(rows[0]) if rows else None
    finally:
        await db.close()


async def is_admin(user_id):
    from bot.config import ADMIN_IDS
    return user_id in ADMIN_IDS


async def set_premium(user_id, value=True):
    db = await _get_db()
    try:
        await db.execute("UPDATE users SET is_premium = ? WHERE user_id = ?", (1 if value else 0, user_id))
        await db.commit()
    finally:
        await db.close()


async def create_goal(user_id, title, description="", target_value=None, unit="", deadline=None):
    db = await _get_db()
    try:
        await db.execute("UPDATE goals SET is_active = 0 WHERE user_id = ? AND is_active = 1", (user_id,))
        await db.execute(
            "INSERT INTO goals (user_id, title, description, target_value, unit, deadline) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, title, description, target_value, unit, deadline)
        )
        await db.commit()
    finally:
        await db.close()


async def get_active_goal(user_id):
    db = await _get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT * FROM goals WHERE user_id = ? AND is_active = 1 ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        )
        return dict(rows[0]) if rows else None
    finally:
        await db.close()


async def get_all_goals(user_id):
    db = await _get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT * FROM goals WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
        )
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def add_daily_log(user_id, goal_id, earned=0, note=None, mood=5):
    db = await _get_db()
    try:
        from datetime import date
        today = date.today().isoformat()
        existing = await db.execute_fetchall(
            "SELECT id FROM daily_logs WHERE user_id = ? AND goal_id = ? AND log_date = ?",
            (user_id, goal_id, today)
        )
        if existing:
            await db.execute(
                "UPDATE daily_logs SET earned = ?, note = ?, mood = ? WHERE id = ?",
                (earned, note, mood, existing[0][0])
            )
        else:
            await db.execute(
                "INSERT INTO daily_logs (user_id, goal_id, log_date, earned, note, mood) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, goal_id, today, earned, note, mood)
            )
        await db.execute(
            "UPDATE goals SET current_value = current_value + ? WHERE id = ?", (earned, goal_id)
        )
        streak_row = await db.execute_fetchall("SELECT * FROM streaks WHERE user_id = ?", (user_id,))
        if streak_row:
            last = streak_row[0][3] if streak_row[0][3] else None
            if last != today:
                if last:
                    from datetime import datetime
                    d1 = datetime.strptime(last, "%Y-%m-%d").date()
                    d2 = datetime.strptime(today, "%Y-%m-%d").date()
                    if (d2 - d1).days == 1:
                        cur = streak_row[0][1] + 1
                        best = max(cur, streak_row[0][2])
                        await db.execute(
                            "UPDATE streaks SET current_streak = ?, best_streak = ?, last_checkin = ? WHERE user_id = ?",
                            (cur, best, today, user_id)
                        )
                    else:
                        await db.execute(
                            "UPDATE streaks SET current_streak = 1, last_checkin = ? WHERE user_id = ?",
                            (today, user_id)
                        )
        else:
            await db.execute(
                "INSERT INTO streaks (user_id, current_streak, best_streak, last_checkin) VALUES (?, 1, 1, ?)",
                (user_id, today)
            )
        await db.commit()
    finally:
        await db.close()


async def get_streak(user_id):
    db = await _get_db()
    try:
        rows = await db.execute_fetchall("SELECT * FROM streaks WHERE user_id = ?", (user_id,))
        return dict(rows[0]) if rows else None
    finally:
        await db.close()


async def get_user_stats(user_id):
    db = await _get_db()
    try:
        goal = None
        rows = await db.execute_fetchall(
            "SELECT * FROM goals WHERE user_id = ? AND is_active = 1 ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        )
        if rows:
            goal = dict(rows[0])
        if not goal:
            return None
        t = await db.execute_fetchall(
            "SELECT SUM(earned) as total FROM daily_logs WHERE user_id = ? AND goal_id = ?",
            (user_id, goal["id"])
        )
        total = t[0][0] if t and t[0][0] else 0
        d = await db.execute_fetchall(
            "SELECT COUNT(*) as days FROM daily_logs WHERE user_id = ? AND goal_id = ?",
            (user_id, goal["id"])
        )
        days = d[0][0] if d else 0
        streak = await db.execute_fetchall("SELECT * FROM streaks WHERE user_id = ?", (user_id,))
        s = dict(streak[0]) if streak else {"current_streak": 0, "best_streak": 0}
        return {"goal": goal, "total_earned": total, "active_days": days, "streak": s}
    finally:
        await db.close()


async def get_logs_for_goal(goal_id, limit=10):
    db = await _get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT * FROM daily_logs WHERE goal_id = ? ORDER BY log_date DESC LIMIT ?",
            (goal_id, limit)
        )
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def add_wish(user_id, text):
    db = await _get_db()
    try:
        from datetime import date
        await db.execute(
            "INSERT INTO wishes (user_id, wish_text, wish_date) VALUES (?, ?, ?)",
            (user_id, text, date.today().isoformat())
        )
        await db.commit()
    finally:
        await db.close()


async def add_thought(user_id, text):
    db = await _get_db()
    try:
        await db.execute("INSERT INTO thoughts (user_id, thought_text) VALUES (?, ?)", (user_id, text))
        await db.commit()
    finally:
        await db.close()


async def get_all_users():
    db = await _get_db()
    try:
        rows = await db.execute_fetchall("SELECT * FROM users ORDER BY created_at DESC")
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_all_active_users():
    db = await _get_db()
    try:
        rows = await db.execute_fetchall("SELECT * FROM users")
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_premium_users():
    db = await _get_db()
    try:
        rows = await db.execute_fetchall("SELECT * FROM users WHERE is_premium = 1")
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_user_count():
    db = await _get_db()
    try:
        rows = await db.execute_fetchall("SELECT COUNT(*) FROM users")
        return rows[0][0]
    finally:
        await db.close()


async def get_premium_count():
    db = await _get_db()
    try:
        rows = await db.execute_fetchall("SELECT COUNT(*) FROM users WHERE is_premium = 1")
        return rows[0][0]
    finally:
        await db.close()


async def search_user(query):
    db = await _get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT * FROM users WHERE username LIKE ? OR first_name LIKE ? OR user_id = ?",
            (f"%{query}%", f"%{query}%", int(query) if query.isdigit() else -1)
        )
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def create_promo(code, days=7, uses=1):
    db = await _get_db()
    try:
        await db.execute(
            "INSERT INTO promo_codes (code, days, total_uses, used_uses) VALUES (?, ?, ?, 0)",
            (code, days, uses)
        )
        await db.commit()
    finally:
        await db.close()


async def use_promo(code):
    db = await _get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT * FROM promo_codes WHERE code = ? AND used_uses < total_uses", (code,)
        )
        if not rows:
            return None, "Промокод не найден или уже использован"
        promo = dict(rows[0])
        await db.execute(
            "UPDATE promo_codes SET used_uses = used_uses + 1 WHERE code = ?", (code,)
        )
        await db.commit()
        return promo, None
    finally:
        await db.close()


async def get_all_promos():
    db = await _get_db()
    try:
        rows = await db.execute_fetchall("SELECT * FROM promo_codes ORDER BY created_at DESC")
        return [dict(r) for r in rows]
    finally:
        await db.close()
