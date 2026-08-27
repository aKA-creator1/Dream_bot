import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import logging
import sqlite3
import json
from datetime import datetime, date

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import BOT_TOKEN, DATABASE_PATH, PROJECT_ROOT
from bot.database import init_db
from bot.handlers import start, goal, checkin, stats, admin
from bot.scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO)


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


async def handle_index():
    path = os.path.join(PROJECT_ROOT, 'webapp', 'templates', 'index.html')
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    return 200, {'content-type': 'text/html'}, content.encode()


async def handle_static(file_path):
    full = os.path.join(PROJECT_ROOT, 'webapp', 'static', file_path)
    if not os.path.exists(full):
        return 404, {'content-type': 'text/plain'}, b'Not found'
    ext = os.path.splitext(full)[1]
    ct = {'css': 'text/css', 'js': 'application/javascript'}.get(ext[1:], 'application/octet-stream')
    with open(full, 'rb') as f:
        return 200, {'content-type': ct}, f.read()


async def handle_user(user_id):
    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not user:
            return 404, {'content-type': 'application/json'}, json.dumps({"error": "not found"}).encode()
        goal_row = db.execute(
            "SELECT * FROM goals WHERE user_id = ? AND is_active = 1 ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        ).fetchone()
        streak = db.execute("SELECT * FROM streaks WHERE user_id = ?", (user_id,)).fetchone()
        logs = []
        goal_data = None
        total_earned = 0
        active_days = 0
        if goal_row:
            goal_data = dict(goal_row)
            for log in db.execute(
                "SELECT * FROM daily_logs WHERE user_id = ? AND goal_id = ? ORDER BY log_date DESC",
                (user_id, goal_row["id"])
            ).fetchall():
                logs.append(dict(log))
            t = db.execute("SELECT SUM(earned) as t FROM daily_logs WHERE user_id = ? AND goal_id = ?",
                           (user_id, goal_row["id"])).fetchone()
            total_earned = t["t"] if t and t["t"] else 0
            d = db.execute("SELECT COUNT(*) as d FROM daily_logs WHERE user_id = ? AND goal_id = ?",
                           (user_id, goal_row["id"])).fetchone()
            active_days = d["d"] if d else 0
        wish = db.execute("SELECT * FROM wishes WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                          (user_id,)).fetchone()
        thoughts = db.execute("SELECT * FROM thoughts WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
                              (user_id,)).fetchall()
        all_goals = db.execute("SELECT * FROM goals WHERE user_id = ? ORDER BY created_at DESC",
                               (user_id,)).fetchall()
        data = {
            "user": dict(user), "goal": goal_data,
            "all_goals": [dict(g) for g in all_goals], "logs": logs,
            "total_earned": total_earned, "active_days": active_days,
            "streak": dict(streak) if streak else {"current_streak": 0, "best_streak": 0},
            "wish": dict(wish) if wish else None,
            "thoughts": [dict(t) for t in thoughts],
        }
        return 200, {'content-type': 'application/json'}, json.dumps(data, default=str).encode()
    finally:
        db.close()


async def handle_checkin(body):
    data = json.loads(body)
    uid = data.get("user_id")
    earned = data.get("earned", 0)
    note = data.get("note")
    mood = data.get("mood", 5)
    if not uid:
        return 400, {'content-type': 'application/json'}, b'{"error":"no user_id"}'
    db = get_db()
    try:
        goal_row = db.execute(
            "SELECT * FROM goals WHERE user_id = ? AND is_active = 1 ORDER BY created_at DESC LIMIT 1",
            (uid,)
        ).fetchone()
        if not goal_row:
            return 400, {'content-type': 'application/json'}, b'{"error":"no active goal"}'
        today = date.today().isoformat()
        ex = db.execute(
            "SELECT id FROM daily_logs WHERE user_id = ? AND goal_id = ? AND log_date = ?",
            (uid, goal_row["id"], today)
        ).fetchone()
        if ex:
            db.execute("UPDATE daily_logs SET earned = ?, note = ?, mood = ? WHERE id = ?",
                       (earned, note, mood, ex["id"]))
        else:
            db.execute(
                "INSERT INTO daily_logs (user_id, goal_id, log_date, earned, note, mood) VALUES (?, ?, ?, ?, ?, ?)",
                (uid, goal_row["id"], today, earned, note, mood))
        db.execute("UPDATE goals SET current_value = current_value + ? WHERE id = ?", (earned, goal_row["id"]))
        db.commit()
        return 200, {'content-type': 'application/json'}, b'{"status":"ok"}'
    finally:
        db.close()


async def handle_wish(body):
    data = json.loads(body)
    uid = data.get("user_id")
    text = data.get("text", "")
    if not uid or not text:
        return 400, {'content-type': 'application/json'}, b'{"error":"missing"}'
    db = get_db()
    try:
        db.execute("INSERT INTO wishes (user_id, wish_text, wish_date) VALUES (?, ?, ?)",
                   (uid, text, date.today().isoformat()))
        db.commit()
        return 200, {'content-type': 'application/json'}, b'{"status":"ok"}'
    finally:
        db.close()


import re


async def asgi_http(scope, receive, send):
    method = scope["method"]
    path = scope["path"]
    body = b''

    if method == "POST":
        while True:
            msg = await receive()
            body += msg.get("body", b"")
            if not msg.get("more_body", False):
                break

    if path == "/" or path == "":
        status, headers, content = await handle_index()
    elif path.startswith("/static/"):
        status, headers, content = await handle_static(path[8:])
    elif re.match(r'^/api/user/(\d+)$', path):
        uid = int(re.match(r'^/api/user/(\d+)$', path).group(1))
        status, headers, content = await handle_user(uid)
    elif path == "/api/checkin" and method == "POST":
        status, headers, content = await handle_checkin(body)
    elif path == "/api/wish" and method == "POST":
        status, headers, content = await handle_wish(body)
    elif path == "/api/stats":
        status, headers, content = 200, {'content-type': 'application/json'}, b'{"total_users":0}'
    else:
        status, headers, content = 404, {'content-type': 'text/plain'}, b'Not found'

    await send({"type": "http.response.start", "status": status, "headers": [
        [k.encode(), v.encode()] for k, v in headers.items()
    ]})
    await send({"type": "http.response.body", "body": content})


async def run_bot():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)
    dp.include_router(goal.router)
    dp.include_router(checkin.router)
    dp.include_router(stats.router)
    dp.include_router(admin.router)
    setup_scheduler(bot)
    logging.info("Бот запущен!")
    await dp.start_polling(bot)


async def app(scope, receive, send):
    if scope["type"] == "lifespan":
        while True:
            msg = await receive()
            if msg["type"] == "lifespan.startup":
                asyncio.create_task(run_bot())
                logging.info("Бот запущен в фоне")
                await send({"type": "lifespan.startup.complete"})
            elif msg["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    elif scope["type"] == "http":
        await asgi_http(scope, receive, send)
