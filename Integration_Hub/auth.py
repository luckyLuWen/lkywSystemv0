"""Local account provisioning and expiring server-side sessions."""
from contextlib import contextmanager
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

DB = Path(os.getenv("LKYW_AUTH_DB", str(Path(__file__).with_name("accounts.sqlite3"))))
router = APIRouter(prefix="/api/auth")
ROLES = ("commander", "dispatcher", "expert", "admin")

@contextmanager
def connect():
    db = sqlite3.connect(DB)
    db.execute("CREATE TABLE IF NOT EXISTS accounts (username TEXT PRIMARY KEY, role TEXT, salt TEXT, digest TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, username TEXT, expires REAL)")
    db.execute("CREATE TABLE IF NOT EXISTS attempts (client TEXT PRIMARY KEY, count INTEGER, started REAL)")
    try:
        with db:
            yield db
    finally:
        db.close()

def digest(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600000).hex()

class Login(BaseModel):
    username: str
    password: str
    role: str

@router.post("/login")
def login(data: Login, request: Request, response: Response):
    client = request.client.host if request.client else "unknown"
    with connect() as db:
        attempt = db.execute("SELECT count, started FROM attempts WHERE client=?", (client,)).fetchone()
        if attempt and time.time() - attempt[1] < 300 and attempt[0] >= 10:
            raise HTTPException(429, "尝试次数过多，请五分钟后重试")
        row = db.execute("SELECT role,salt,digest FROM accounts WHERE username=?", (data.username,)).fetchone()
        valid = hmac.compare_digest(digest(data.password, row[1] if row else "00" * 16), row[2] if row else "00" * 32)
        if not row or not valid or row[0] != data.role:
            count = attempt[0] + 1 if attempt and time.time() - attempt[1] < 300 else 1
            started = attempt[1] if count > 1 else time.time()
            db.execute("INSERT OR REPLACE INTO attempts VALUES (?,?,?)", (client,count,started))
            db.commit()
            raise HTTPException(401, "账号、密码或所选角色不正确")
        db.execute("DELETE FROM attempts WHERE client=?", (client,))
        token = secrets.token_urlsafe(32)
        db.execute("INSERT INTO sessions VALUES (?,?,?)", (hashlib.sha256(token.encode()).hexdigest(),data.username,time.time()+28800))
    response.set_cookie("lkyw_session", token, httponly=True, samesite="strict", secure=request.url.scheme == "https", max_age=28800)
    return {"username":data.username,"role":row[0]}

@router.get("/session")
def session(request: Request):
    token = hashlib.sha256(request.cookies.get("lkyw_session", "").encode()).hexdigest()
    with connect() as db:
        row = db.execute("SELECT a.username,a.role FROM sessions s JOIN accounts a ON s.username=a.username WHERE s.token=? AND s.expires>?", (token,time.time())).fetchone()
    if not row:
        raise HTTPException(401, "请先登录")
    return {"username":row[0],"role":row[1]}

@router.post("/logout")
def logout(request: Request, response: Response):
    token = hashlib.sha256(request.cookies.get("lkyw_session", "").encode()).hexdigest()
    with connect() as db:
        db.execute("DELETE FROM sessions WHERE token=?", (token,))
    response.delete_cookie("lkyw_session")
    return {"ok":True}

if __name__ == "__main__":
    import getpass
    username = input("Account: ").strip()
    role = input("Role (commander/dispatcher/expert/admin): ").strip()
    password = getpass.getpass("Password (at least 8 characters): ")
    if not username or role not in ROLES or len(password) < 8:
        raise SystemExit("Invalid account, role or password")
    salt = secrets.token_hex(16)
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO accounts VALUES (?,?,?,?)", (username,role,salt,digest(password,salt)))
        db.execute("DELETE FROM sessions WHERE username=?", (username,))
    print("Account saved")
