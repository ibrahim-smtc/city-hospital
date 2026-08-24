import os
import sqlite3

def replace_in_files():
    for root, dirs, files in os.walk('.'):
        if 'virtual' in root or '.git' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.endswith(('.py', '.html', '.js', '.css', '.md', '.txt')):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if 'New Care Med Center' in content:
                        new_content = content.replace('New Care Med Center', 'New Care Med Center')
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f'Updated {path}')
                except Exception as e:
                    pass

def update_db():
    try:
        conn = sqlite3.connect('hospital.db')
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in c.fetchall()]
        
        for table in tables:
            c.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in c.fetchall() if row[2] in ('TEXT', 'VARCHAR')]
            
            for col in columns:
                try:
                    c.execute(f"UPDATE {table} SET {col} = REPLACE({col}, 'New Care Med Center', 'New Care Med Center')")
                    conn.commit()
                except Exception as e:
                    pass
        print('Updated Database')
        conn.close()
    except Exception as e:
        print('DB Error:', e)

replace_in_files()
update_db()
