from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database.index import Base


# 用户表：用户名 + 哈希后的密码，用来支持登录和「我的行程」
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    trips = relationship("Trip", back_populates="user")

    def to_dict(self):
        return {"id": self.id, "username": self.username, "nickname": self.nickname or self.username}


# 定义旅行计划主表
class Trip(Base):
    __tablename__ = "trips"

    # id列
    id = Column(Integer, primary_key=True, index=True)
    # 目的地列：字符串，建立索引（因为经常需要按目的地搜索）
    destination = Column(String, index=True)
    # 出发地：为空表示老数据（只规划了目的地市内行程）
    origin = Column(String, nullable=True)
    # 出发日期列：Date 类型
    start_date = Column(Date)
    # 结束日期列：Date 类型
    end_date = Column(Date)
    # 状态列：字符串，默认值是 "planning"（规划中）
    status = Column(String, default="planning")
    # 用户填写的总预算与出行人数，用于工作台的预算面板（老数据可能为空）
    budget = Column(Float, nullable=True)
    travelers = Column(Integer, nullable=True)
    # 城际交通 / 酒店 / 预算方案的 JSON 快照（由 Agent 生成）
    plan_json = Column(Text, nullable=True)
    # 归属用户：游客创建的行程为空，登录后创建/认领的行程会写进这里
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    user = relationship("User", back_populates="trips")


    # 关联关系：一个 Trip 包含多个 TripDay
    # back_populates="trip" 表示：在 TripDay 类中，反向对应的属性名叫 trip
    days = relationship(
        "TripDay",
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="TripDay.day_index",
    )
    # 注：cascade="all, delete-orphan" 的意思是，如果删除了 Trip，它下面的所有 Day 也会被级联删除

# 定义每日行程表
class TripDay(Base):
    __tablename__ = "trip_days"

    id = Column(Integer, primary_key=True, index=True)
    # 外键列：关联到 trips 表的 id
    trip_id = Column(Integer, ForeignKey("trips.id"))
    # 第几天（比如第1天、第2天）
    day_index = Column(Integer)
    # 具体日期
    date = Column(Date)

    # 反向关联：指向 Trip
    trip = relationship("Trip", back_populates="days")
    # 关联关系：一天包含多个行程项（TripItem）
    items = relationship("TripItem", back_populates="day", cascade="all, delete-orphan")

# 定义具体行程项表
class TripItem(Base):
    __tablename__ = "trip_items"

    id = Column(Integer, primary_key=True, index=True)
    # 外键列：关联到 trip_days 表的 id
    trip_day_id = Column(Integer, ForeignKey("trip_days.id"))
    # 景点名称
    place_name = Column(String)
    # 开始时间（MVP阶段简化处理，直接用字符串 "09:30"）
    start_time = Column(String)
    # 结束时间
    end_time = Column(String)
    # 行程项类别：sightseeing / food / shopping / entertainment / other
    category = Column(String, nullable=True)
    # 预估花费（浮点数），默认 0.0
    cost_estimate = Column(Float, default=0.0)
    # 备注：如「建议点招牌菜」「需提前预约」
    note = Column(String, nullable=True)

    # 新增经纬度字段
    lng = Column(Float, nullable=True)
    lat = Column(Float, nullable=True)

    # 反向关联：指向 TripDay
    day = relationship("TripDay", back_populates="items")

    
