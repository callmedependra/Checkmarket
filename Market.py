import requests
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
import schedule
import time
import json
import smtplib
from email.mime.text import MIMEText


LOGINURL = "https://uat.ssl.com.np/atsweb/login"
MARKET_STATUS_URL = "https://uat.ssl.com.np/atsweb/home?action=marketStatus"

USERNAME = "DpAdvisor"
PASSWORD = "Test@1234"

DB_NAME = "market_status.db"

SENDER_EMAIL = "dipendra.yhhits@gmail.com"
SENDER_PASSWORD = "cnkp tqsc svcz dvvt"
RECEIVER_EMAILS = [
    "himanshu.dhakal@dghub.io",
    "adarshsapkota10@gmail.com",
    "callmedependra@gmail.com"
]


# ================= DATABASE =================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def send_market_email(status):
    kathmandu_time = datetime.now(ZoneInfo("Asia/Kathmandu"))

    subject = f"Market Status Update: {status}"
    body = f"""
Market Status Changed of  User Acceptance Testing (UAT) environment for ATrad's online stock trading platform in Nepal

New Status: {status}
Time (Asia/Kathmandu): {kathmandu_time.strftime('%Y-%m-%d %H:%M:%S')}
"""

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(RECEIVER_EMAILS)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAILS, msg.as_string())
            print(f"[{kathmandu_time}]  Email sent ({status})")
    except Exception as e:
        print(f"[{kathmandu_time}]  Email failed: {e}")




def login(session):
    try:
        session.get(LOGINURL)

        payload = {
            "txtUserName": USERNAME,
            "txtPassword": PASSWORD,
            "action": "login",
            "format": "json"
        }

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = session.post(LOGINURL, data=payload, headers=headers)

        if response.status_code == 200:
            print(f"[{datetime.now()}]  Login successful")
            return True

        print(f"[{datetime.now()}]  Login failed")
        return False

    except Exception as e:
        print(f"[{datetime.now()}]  Login error: {e}")
        return False


def get_market_status(session):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    response = session.get(MARKET_STATUS_URL, headers=headers)

    # 🔁 Session expired → re-login
    if response.status_code == 401 or "session expired" in response.text.lower():
        print(f"[{datetime.now()}] Session expired → Re-login")
        if not login(session):
            return None
        response = session.get(MARKET_STATUS_URL, headers=headers)

    if response.status_code != 200:
        print(f"[{datetime.now()}]  Market fetch failed")
        return None

    try:
        response_text = response.text.replace("'", '"')
        json_response = json.loads(response_text)
        return parse_market_status(json_response)
    except Exception as e:
        print(f"[{datetime.now()}]  Parse error: {e}")
        return None


def parse_market_status(json_data):
    try:
        data = json_data.get("data", {})
        status = data.get("status", "").upper()

        if "OPEN" in status and "PRE" not in status:
            return "OPEN"
        elif "PRE" in status:
            return "PRE_OPEN"
        elif "CLOSE" in status:
            return "CLOSED"
        elif "HOLIDAY" in status:
            return "HOLIDAY"
    except:
        pass

    return None
 


def store_market_status(status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT status FROM market_status ORDER BY id DESC LIMIT 1")
    last = cursor.fetchone()

    # Always print current status
    print(f"[{datetime.now()}] Current Market Status: {status}")

    # Insert only if changed
    if last is None or last[0] != status:
        cursor.execute(
            "INSERT INTO market_status (status) VALUES (?)",
            (status,)
        )
        conn.commit()
        print(f"[{datetime.now()}]  Status changed → {status}")
        send_market_email(status)
    else:
        print(f"[{datetime.now()}] Status unchanged → {status}")

    conn.close()

# ============================================


# ================= JOB =======================

def job():
    print(f"\n[{datetime.now()}]  Running every Minute.")  # Log start of job

    session = requests.Session()

    if not login(session):
        print(f"[{datetime.now()}] Job aborted due to login failure")
        return

    status = get_market_status(session)

    if status:
        store_market_status(status)  # Handles DB + email + printing
    else:
        print(f"[{datetime.now()}]  Could not fetch market status")

# ============================================


# ================= MAIN ======================

def main():
    init_db()

    print("\n" + "=" * 60)
    print("NEPSE UAT ATrad UAT testing")
    print("=" * 60)

    job()  # run once immediately

    schedule.every(1).minutes.do(job)  # schedule job every 1 minute
    

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped by Dipendra.")



if __name__ == "__main__":
    main()
