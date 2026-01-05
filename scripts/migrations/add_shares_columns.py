"""
添加目标股数列到 position_targets 表
"""

import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from core.database import Database
from config import DATABASE_PATH

db = Database(DATABASE_PATH)
conn = db.get_connection()
cursor = conn.cursor()

print("正在检查并添加股数列...")

try:
    # 检查列是否已存在
    cursor.execute("PRAGMA table_info(position_targets)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'target_shares' not in columns:
        print("  添加 target_shares 列...")
        cursor.execute("""
            ALTER TABLE position_targets
            ADD COLUMN target_shares INTEGER
        """)
        print("  ✓ target_shares 列添加成功")
    else:
        print("  ✓ target_shares 列已存在")

    if 'max_shares' not in columns:
        print("  添加 max_shares 列...")
        cursor.execute("""
            ALTER TABLE position_targets
            ADD COLUMN max_shares INTEGER
        """)
        print("  ✓ max_shares 列添加成功")
    else:
        print("  ✓ max_shares 列已存在")

    conn.commit()
    print("\n✅ 数据库更新成功！")

except Exception as e:
    print(f"\n❌ 错误: {e}")
    conn.rollback()
finally:
    conn.close()
