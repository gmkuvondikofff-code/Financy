from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    fullname = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    business_type = Column(String)
    business_name = Column(String)
    # Foydalanuvchining chat sessiyalari
    chat_sessions = relationship("ChatSession", back_populates="owner")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String)
    user_email = Column(String)
    batches = relationship("ProductBatch", back_populates="parent_product")

class ProductBatch(Base):
    __tablename__ = "product_batches"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    entry_price = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    store_name = Column(String)
    parent_product = relationship("Product", back_populates="batches")

class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    category = Column(String)
    amount = Column(Float)
    date = Column(DateTime, default=datetime.datetime.utcnow)

class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String)
    product_name = Column(String)
    quantity = Column(Integer)
    sell_price = Column(Float)
    buy_price = Column(Float)
    profit = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Debt(Base):
    __tablename__ = "debts"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String)
    customer_name = Column(String)
    phone = Column(String)
    product_name = Column(String)
    quantity = Column(Integer)
    total_amount = Column(Float)
    remaining_amount = Column(Float)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    payments = relationship("DebtPayment", back_populates="parent_debt")

class DebtPayment(Base):
    __tablename__ = "debt_payments"
    id = Column(Integer, primary_key=True, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id"))
    pay_amount = Column(Float)
    pay_date = Column(DateTime, default=datetime.datetime.utcnow)
    parent_debt = relationship("Debt", back_populates="payments")

# --- YANGI QO'SHILGAN CHAT JADVALLARI ---

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String) # Masalan: "Bugungi savdo tahlili"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    owner = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String) # "user" yoki "assistant"
    content = Column(Text) # Xabar matni
    image_url = Column(String, nullable=True) # Agar rasm yuborilsa, uning yo'li
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    session = relationship("ChatSession", back_populates="messages")