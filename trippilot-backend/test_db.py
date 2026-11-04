from sqlalchemy import create_engine, text
from config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text("SELECT version();"))
    print("数据库连接成功，版本信息：", result.fetchone()[0])