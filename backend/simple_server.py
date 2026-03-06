import http.server
import socketserver
import json
import sqlite3
import os
import secrets
from urllib.parse import urlparse, parse_qs
import hashlib

# Configuration
# Configuration
PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "marketplace.db")
STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

# Database Init
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'buyer',
            location TEXT,
            phone TEXT
        );
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            title TEXT,
            category TEXT,
            brand TEXT,
            model TEXT,
            condition TEXT,
            price REAL,
            location TEXT,
            description TEXT,
            status TEXT DEFAULT 'active',
            working_parts TEXT,
            photos TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(seller_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS buy_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER,
            buyer_id INTEGER,
            seller_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(listing_id) REFERENCES listings(id)
        );
    ''')
    
    # Migration: Add phone column if it doesn't exist (for existing DBs)
    try:
        c.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    except sqlite3.OperationalError:
        pass # Column likely exists

    # Check if admin exists
    c.execute("SELECT id FROM users WHERE role='admin'")
    if not c.fetchone():
        print("Creating default admin user...")
        pwd_hash = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT INTO users (name, email, password_hash, role, location, phone) VALUES (?, ?, ?, ?, ?, ?)",
                  ("Administrator", "admin@example.com", pwd_hash, "admin", "HQ", "0000000000"))
        print("Default admin created: admin@example.com / admin123")
    
    conn.commit()
    conn.close()

class MarketplaceHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_error(self, code, message=None, explain=None):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'detail': message}).encode())

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        # Static Files serving from /static
        if path.startswith("/static/"):
            # Rewriting path to serve from frontend dir
            relative_path = path.replace("/static/", "")
            file_path = os.path.join(STATIC_DIR, relative_path)
            if os.path.exists(file_path):
                self.send_response(200)
                # Guess mimetype
                if file_path.endswith(".html"): self.send_header('Content-type', 'text/html')
                elif file_path.endswith(".js"): self.send_header('Content-type', 'application/javascript')
                elif file_path.endswith(".css"): self.send_header('Content-type', 'text/css')
                self.end_headers()
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "File not found")
                return
        
        # Root -> Index
        if path == "/":
            self.send_response(301)
            self.send_header('Location', '/static/index.html')
            self.end_headers()
            return

        # API: Get Listings
        if path == "/listings/":
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM listings ORDER BY created_at DESC")
            listings = [dict(row) for row in c.fetchall()]
            # Add photos array (fake for now or parsed)
            for l in listings:
                l['photos'] = json.loads(l['photos']) if l['photos'] else []
            conn.close()
            self.send_json(listings)
            return
            
        # API: My Requests
        if path == "/requests/my-requests":
            user = self.get_user_from_token()
            if not user: return
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM buy_requests WHERE buyer_id=?", (user['id'],))
            requests = [dict(row) for row in c.fetchall()]
            conn.close()
            self.send_json(requests)
            return

        # API: Incoming Requests
        if path == "/requests/incoming":
            user = self.get_user_from_token()
            if not user: return
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            # Join with users to get buyer info
            c.execute('''
                SELECT br.*, u.name as buyer_name, u.email as buyer_email, u.phone as buyer_phone, u.location as buyer_location
                FROM buy_requests br
                JOIN users u ON br.buyer_id = u.id
                WHERE br.seller_id=?
            ''', (user['id'],))
            requests = [dict(row) for row in c.fetchall()]
            conn.close()
            self.send_json(requests)
            return
            
        # API: Auth Me
        if path == "/auth/me":
            user = self.get_user_from_token()
            if not user: return
            self.send_json(user)
            return

        self.send_error(404)

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length'))
            body = json.loads(self.rfile.read(length))
            parsed = urlparse(self.path)
            path = parsed.path

            # API: Login
            if path == "/auth/login":
                conn = sqlite3.connect(DB_FILE)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                pwd_hash = hashlib.sha256(body['password'].encode()).hexdigest()
                c.execute("SELECT * FROM users WHERE email=? AND password_hash=?", (body['email'], pwd_hash))
                user = c.fetchone()
                conn.close()
                
                if user:
                    token = f"{user['id']}:{secrets.token_hex(16)}"
                    user_dict = dict(user)
                    del user_dict['password_hash']
                    self.send_json({"access_token": token, "user": user_dict})
                else:
                    self.send_error(401, "Invalid credentials")
                return

            # API: Register
            if path == "/auth/register":
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                pwd_hash = hashlib.sha256(body['password'].encode()).hexdigest()
                try:
                    c.execute("INSERT INTO users (name, email, password_hash, role, location, phone) VALUES (?, ?, ?, ?, ?, ?)",
                              (body['name'], body['email'], pwd_hash, body['role'], body['location'], body.get('phone', '')))
                    conn.commit()
                    user_id = c.lastrowid
                    conn.close()
                    token = f"{user_id}:{secrets.token_hex(16)}"
                    self.send_json({"access_token": token, "user": {**body, "id": user_id, "password": ""}})
                except sqlite3.IntegrityError:
                    self.send_error(400, "Email already exists")
                except Exception as e:
                    print(f"Registration Error: {e}")
                    self.send_error(500, f"Registration failed: {str(e)}")
                return

            # API: Create Listing
            if path == "/listings/":
                user = self.get_user_from_token()
                if not user: return
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('''INSERT INTO listings (seller_id, title, category, brand, model, condition, price, location, description, working_parts, photos)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (user['id'], body['title'], body['category'], body['brand'], body['model'], 
                           body['condition'], body['price'], body['location'], body['description'], 
                           body['working_parts'], json.dumps(body['photos'])))
                conn.commit()
                lid = c.lastrowid
                conn.close()
                self.send_json({"id": lid, "status": "active"})
                return

            # API: Create Request
            if path == "/requests/":
                user = self.get_user_from_token()
                if not user: return
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT seller_id FROM listings WHERE id=?", (body['listing_id'],))
                listing = c.fetchone()
                if not listing:
                    self.send_error(404, "Listing not found")
                    return
                
                c.execute("INSERT INTO buy_requests (listing_id, buyer_id, seller_id) VALUES (?, ?, ?)",
                          (body['listing_id'], user['id'], listing[0]))
                conn.commit()
                rid = c.lastrowid
                conn.close()
                self.send_json({"id": rid, "status": "pending"})
                return

        except Exception as e:
            print(f"Server Error: {e}")
            self.send_error(500, str(e))

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        # API: Accept/Reject Request
        if path.startswith("/requests/"):
            user = self.get_user_from_token()
            if not user: return
            parts = path.strip("/").split("/")
            req_id = int(parts[1])
            action = parts[2] # accept/reject
            
            status = "accepted" if action == "accept" else "rejected"
            
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE buy_requests SET status=? WHERE id=?", (status, req_id))
            conn.commit()
            conn.close()
            self.send_json({"id": req_id, "status": status})
            return

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def get_user_from_token(self):
        auth_header = self.headers.get('Authorization')
        if not auth_header or not auth_header.startswith("Bearer "):
            self.send_error(401, "Unauthorized")
            return None
        token = auth_header.split(" ")[1]
        try:
            user_id = int(token.split(":")[0])
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE id=?", (user_id,))
            user = c.fetchone()
            conn.close()
            if not user:
                 self.send_error(401, "Invalid User")
                 return None
            return dict(user)
        except:
            self.send_error(401, "Invalid Token")
            return None

if __name__ == "__main__":
    init_db()
    # os.chdir(os.path.dirname(os.path.abspath(__file__))) - Removed to avoid CWD confusion
    server = socketserver.TCPServer(("", PORT), MarketplaceHandler)
    print(f"Serving at http://localhost:{PORT}")
    server.serve_forever()
