import http.server
import socketserver
import json
import sqlite3
import os
import secrets
from urllib.parse import urlparse, parse_qs
import hashlib

# Configuration
PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "marketplace.db")
STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

# Database Init
def init_db():
    conn = sqlite3.connect(DB_FILE, timeout=10)
    try:
        # Enable WAL (Write-Ahead Logging) for better concurrency
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
        except:
            pass
            
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
                seller_price REAL, -- Amount seller receives
                price REAL, -- Amount buyer pays (Display Price)
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
        
        # Migration: Add columns if they don't exist
        try:
            c.execute("ALTER TABLE users ADD COLUMN phone TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            c.execute("ALTER TABLE listings ADD COLUMN seller_price REAL")
            # Backfill existing listings: seller_price = price
            c.execute("UPDATE listings SET seller_price = price WHERE seller_price IS NULL")
        except sqlite3.OperationalError:
            pass

        # Check if admin exists
        c.execute("SELECT id FROM users WHERE role='admin'")
        if not c.fetchone():
            print("Creating default admin user...")
            pwd_hash = hashlib.sha256("admin123".encode()).hexdigest()
            c.execute("INSERT INTO users (name, email, password_hash, role, location, phone) VALUES (?, ?, ?, ?, ?, ?)",
                      ("Administrator", "admin@example.com", pwd_hash, "admin", "HQ", "0000000000"))
            print("Default admin created: admin@example.com / admin123")
        
        conn.commit()
    finally:
        conn.close()

class MarketplaceHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
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
        
        # Static Files serving
        if path.startswith("/static/"):
            relative_path = path.replace("/static/", "")
            file_path = os.path.join(STATIC_DIR, relative_path)
            if os.path.exists(file_path):
                self.send_response(200)
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
            conn = sqlite3.connect(DB_FILE, timeout=10)
            try:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                # Determine user role from token (optional) to show/hide seller_price?
                # Only show ACTIVE listings to the public
                c.execute("SELECT id, seller_id, title, category, brand, model, condition, price, location, description, status, working_parts, photos, created_at FROM listings WHERE status='active' ORDER BY created_at DESC")
                listings = [dict(row) for row in c.fetchall()]
                for l in listings:
                    l['photos'] = json.loads(l['photos']) if l['photos'] else []
            finally:
                conn.close()
            self.send_json(listings)
            return

        # API: My Requests (As Buyer)
        if path == "/requests/my-requests":
            user, error = self.get_user_from_token()
            if error:
                self.send_error(401, error)
                return
            conn = sqlite3.connect(DB_FILE, timeout=10)
            try:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT * FROM buy_requests WHERE buyer_id=?", (user['id'],))
                requests = [dict(row) for row in c.fetchall()]
            finally:
                conn.close()
            self.send_json(requests)
            return

        # API: Incoming Requests (As Seller)
        if path == "/requests/incoming":
            user, error = self.get_user_from_token()
            if error:
                self.send_error(401, error)
                return
            conn = sqlite3.connect(DB_FILE, timeout=10)
            try:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute('''
                    SELECT br.*, u.name as buyer_name, u.location as buyer_location
                    FROM buy_requests br
                    JOIN users u ON br.buyer_id = u.id
                    WHERE br.seller_id=?
                ''', (user['id'],))
                # Note: REMOVED u.email, u.phone from SELECT to enforce privacy
                requests = [dict(row) for row in c.fetchall()]
            finally:
                conn.close()
            self.send_json(requests)
            return
            
        # API: Auth Me
        if path == "/auth/me":
            user, error = self.get_user_from_token()
            if error:
                self.send_error(401, error)
                return
            self.send_json(user)
            return

        # API: Admin - Get All Users
        if path == "/admin/users":
            user, error = self.get_user_from_token()
            if error:
                self.send_error(401, error)
                return
            if user['role'] != 'admin':
                self.send_error(403, "Admin access required")
                return
            
            conn = sqlite3.connect(DB_FILE, timeout=10)
            try:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT id, name, email, role, location, phone FROM users")
                users = [dict(row) for row in c.fetchall()]
            finally:
                conn.close()
            self.send_json(users)
            return
            
        # API: Admin - Get All Listings (With Profit Info)
        if path == "/admin/listings_full":
            user, error = self.get_user_from_token()
            if error:
                self.send_error(401, error)
                return
            if user['role'] != 'admin':
                self.send_error(403, "Admin access required")
                return
            
            conn = sqlite3.connect(DB_FILE, timeout=10)
            try:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT * FROM listings ORDER BY created_at DESC")
                listings = [dict(row) for row in c.fetchall()]
                for l in listings:
                    l['profit'] = (l['price'] or 0) - (l['seller_price'] or (l['price'] or 0)) 
            finally:
                conn.close()
            self.send_json(listings)
            return

        # API: Admin - Get Sold Items
        if path == "/admin/sold_items":
            user, error = self.get_user_from_token()
            if error:
                self.send_error(401, error)
                return
            if user['role'] != 'admin':
                self.send_error(403, "Admin access required")
                return

            conn = sqlite3.connect(DB_FILE, timeout=10)
            try:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                query = '''
                    SELECT 
                        l.id, l.title, l.price, l.seller_price, l.category,
                        br.updated_at as sold_date,
                        b.name as buyer_name, b.email as buyer_email, b.phone as buyer_phone,
                        s.name as seller_name, s.email as seller_email, s.phone as seller_phone
                    FROM buy_requests br
                    JOIN listings l ON br.listing_id = l.id
                    JOIN users b ON br.buyer_id = b.id
                    JOIN users s ON l.seller_id = s.id
                    WHERE br.status = 'accepted'
                    ORDER BY br.updated_at DESC
                '''
                c.execute(query)
                sold_items = [dict(row) for row in c.fetchall()]
                for item in sold_items:
                     item['profit'] = (item['price'] or 0) - (item['seller_price'] or (item['price'] or 0))
            finally:
                conn.close()
            self.send_json(sold_items)
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
                conn = sqlite3.connect(DB_FILE, timeout=10)
                try:
                    conn.row_factory = sqlite3.Row
                    c = conn.cursor()
                    pwd_hash = hashlib.sha256(body['password'].encode()).hexdigest()
                    c.execute("SELECT * FROM users WHERE email=? AND password_hash=?", (body['email'], pwd_hash))
                    user = c.fetchone()
                finally:
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
                conn = sqlite3.connect(DB_FILE, timeout=10)
                try:
                    c = conn.cursor()
                    pwd_hash = hashlib.sha256(body['password'].encode()).hexdigest()
                    try:
                        c.execute("INSERT INTO users (name, email, password_hash, role, location, phone) VALUES (?, ?, ?, ?, ?, ?)",
                                  (body['name'], body['email'], pwd_hash, body['role'], body['location'], body.get('phone', '')))
                        conn.commit()
                        user_id = c.lastrowid
                        token = f"{user_id}:{secrets.token_hex(16)}"
                        self.send_json({"access_token": token, "user": {**body, "id": user_id, "password": ""}})
                    except sqlite3.IntegrityError:
                        self.send_error(400, "Email already exists")
                    except Exception as e:
                        print(f"Registration Error: {e}")
                        self.send_error(500, f"Registration failed: {str(e)}")
                finally:
                    conn.close()
                return

            # API: Create Listing
            if path == "/listings/":
                user, error = self.get_user_from_token()
                if error: 
                    self.send_error(401, error)
                    return
                conn = sqlite3.connect(DB_FILE, timeout=10)
                try:
                    seller_price = float(body['price']) # The input 'price' is what the seller WANTS
                    # Markup Logic: +10% + 20 flat fee
                    display_price = (seller_price * 1.10) + 20 
                    # Rounding
                    display_price = round(display_price, 2)
                    
                    c = conn.cursor()
                    c.execute('''INSERT INTO listings (seller_id, title, category, brand, model, condition, seller_price, price, location, description, working_parts, photos)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                              (user['id'], body['title'], body['category'], body['brand'], body['model'], 
                               body['condition'], seller_price, display_price, body['location'], body['description'], 
                               body['working_parts'], json.dumps(body['photos'])))
                    conn.commit()
                    lid = c.lastrowid
                    self.send_json({"id": lid, "status": "active", "price": display_price})
                finally:
                    conn.close()
                return

            # API: Create Request
            if path == "/requests/":
                user, error = self.get_user_from_token()
                if error:
                    self.send_error(401, error)
                    return
                conn = sqlite3.connect(DB_FILE, timeout=10)
                try:
                    c = conn.cursor()
                    
                    # CHECK LIMIT: Check if user already has a PENDING request for this listing
                    c.execute("SELECT id FROM buy_requests WHERE listing_id=? AND buyer_id=? AND status='pending'", (body['listing_id'], user['id']))
                    existing = c.fetchone()
                    if existing:
                         # Use 400 Bad Request
                         self.send_error(400, "You already have a pending request for this item.")
                         return

                    c.execute("SELECT seller_id FROM listings WHERE id=?", (body['listing_id'],))
                    listing = c.fetchone()
                    if not listing:
                        self.send_error(404, "Listing not found")
                        return 
                    
                    c.execute("INSERT INTO buy_requests (listing_id, buyer_id, seller_id) VALUES (?, ?, ?)",
                              (body['listing_id'], user['id'], listing[0]))
                    conn.commit()
                    rid = c.lastrowid
                    self.send_json({"id": rid, "status": "pending"})
                finally:
                    conn.close()
                return

        except Exception as e:
            print(f"Server Error: {e}")
            self.send_error(500, str(e))

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        # API: Accept/Reject Request
        if path.startswith("/requests/"):
            user, error = self.get_user_from_token()
            if error:
                self.send_error(401, error)
                return
            parts = path.strip("/").split("/")
            req_id = int(parts[1])
            action = parts[2] # accept/reject
            
            status = "accepted" if action == "accept" else "rejected"
            
            conn = sqlite3.connect(DB_FILE, timeout=10)
            try:
                c = conn.cursor()
                if status == 'accepted':
                    c.execute("UPDATE buy_requests SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (status, req_id))
                    # Mark listing as SOLD
                    c.execute("UPDATE listings SET status='sold' WHERE id=(SELECT listing_id FROM buy_requests WHERE id=?)", (req_id,))
                else:
                    c.execute("UPDATE buy_requests SET status=? WHERE id=?", (status, req_id))
                conn.commit()
            finally:
                conn.close()
            self.send_json({"id": req_id, "status": status})
            return

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        user, error = self.get_user_from_token()
        if error:
            self.send_error(401, error)
            return
            
        if user['role'] != 'admin':
            self.send_error(403, "Admin access required")
            return

        try:
            # API: Admin - Delete User
            if path.startswith("/admin/users/"):
                parts = path.strip("/").split("/")
                user_id_to_delete = int(parts[2])
                
                if user_id_to_delete == user['id']:
                    self.send_error(400, "Cannot delete yourself")
                    return

                conn = sqlite3.connect(DB_FILE, timeout=10)
                try:
                    c = conn.cursor()
                    # Cascade delete (simple approach: manual delete related items)
                    c.execute("DELETE FROM listings WHERE seller_id=?", (user_id_to_delete,))
                    c.execute("DELETE FROM buy_requests WHERE buyer_id=? OR seller_id=?", (user_id_to_delete, user_id_to_delete))
                    c.execute("DELETE FROM users WHERE id=?", (user_id_to_delete,))
                    conn.commit()
                    self.send_json({"status": "deleted", "id": user_id_to_delete})
                finally:
                    conn.close()
                return

            # API: Admin - Delete Listing
            if path.startswith("/admin/listings/"):
                parts = path.strip("/").split("/")
                listing_id = int(parts[2])
                
                conn = sqlite3.connect(DB_FILE, timeout=10)
                try:
                    c = conn.cursor()
                    c.execute("DELETE FROM buy_requests WHERE listing_id=?", (listing_id,))
                    c.execute("DELETE FROM listings WHERE id=?", (listing_id,))
                    conn.commit()
                    self.send_json({"status": "deleted", "id": listing_id})
                finally:
                    conn.close()
                return

            self.send_error(404, "Endpoint not found")

        except Exception as e:
            print(f"Delete Error: {e}")
            self.send_error(500, str(e))

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def get_user_from_token(self):
        auth_header = self.headers.get('Authorization')
        if not auth_header or not auth_header.startswith("Bearer "):
            return None, "Unauthorized"
        token = auth_header.split(" ")[1]
        try:
            user_id = int(token.split(":")[0])
            conn = sqlite3.connect(DB_FILE, timeout=10)
            try:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT * FROM users WHERE id=?", (user_id,))
                user = c.fetchone()
            finally:
                conn.close()
            if not user:
                 return None, "Invalid User"
            return dict(user), None
        except:
            return None, "Invalid Token"

if __name__ == "__main__":
    init_db()
    server = socketserver.TCPServer(("", PORT), MarketplaceHandler)
    print(f"Serving at http://localhost:{PORT}")
    server.serve_forever()
