import sqlite3

try:
    conn = sqlite3.connect('backend/marketplace.db')
    c = conn.cursor()
    # Hash for '123456'
    new_hash = '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92'
    email = 'smax06388@gmail.com'
    
    c.execute("UPDATE users SET password_hash=? WHERE email=?", (new_hash, email))
    conn.commit()
    
    if c.rowcount > 0:
        print(f"Successfully reset password for {email}")
    else:
        print(f"User {email} not found")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
