from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime
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
    email = Column(String, index=True)  # Foydalanuvchini aniqlash uchun
    category = Column(String)           # Ijara, Soliq va h.k.
    amount = Column(Float)             # Xarajat miqdori
    date = Column(DateTime, default=datetime.datetime.utcnow)

class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String)
    product_name = Column(String)
    quantity = Column(Integer)
    sell_price = Column(Float)      # Sotilgan narxi
    buy_price = Column(Float)       # Olingan narxi (Foydani hisoblash uchun)
    profit = Column(Float)          # Sof foyda (sell_price - buy_price) * quantity
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Debt(Base):
    __tablename__ = "debts"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String)
    customer_name = Column(String)
    phone = Column(String)
    product_name = Column(String)   # Qaysi tovar berildi
    quantity = Column(Integer)      # Necha dona berildi
    total_amount = Column(Float)    # Umumiy qarz summasi
    remaining_amount = Column(Float) # Qolgan qarz (to'langan sari kamayadi)
    status = Column(String, default="active") # active / closed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    # To'lovlar tarixi bilan bog'lanish
    payments = relationship("DebtPayment", back_populates="parent_debt")

class DebtPayment(Base):
    __tablename__ = "debt_payments"
    id = Column(Integer, primary_key=True, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id"))
    pay_amount = Column(Float)      # Safar qancha to'ladi
    pay_date = Column(DateTime, default=datetime.datetime.utcnow)
    parent_debt = relationship("Debt", back_populates="payments")