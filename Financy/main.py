import random
import smtplib
import json
from email.message import EmailMessage
from email.utils import formataddr
from typing import Optional
from fastapi import FastAPI, Request, Form, Depends ,File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models
from database import engine, get_db , Base
from ai_service import get_ai_response  # Mana shu qator funksiyani ulaydi
from datetime import datetime, timedelta
from sqlalchemy import func , desc
from models import Expense  # Agar models.py faylida bo'lsa

import os
import uuid
from fastapi.staticfiles import StaticFiles

# Bu qator jadval yo'q bo'lsa, uni yaratib beradi
Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Vaqtinchalik ma'lumotlarni saqlash (Kesh yoki DB yaxshi, lekin hozircha shu ham bo'ladi)
temp_reg_data = {}

def send_otp(email: str, code: str):
    SENDER_EMAIL = "gm.kuvondikofff@gmail.com"
    SENDER_PASSWORD = "tdow vzjx tppt hzrh" 
    msg = EmailMessage()
    msg['Subject'] = "Financy.uz - Tasdiqlash kodi"
    msg['From'] = formataddr(("Financy.uz", SENDER_EMAIL))
    msg['To'] = email
    msg.set_content(f"Sizning tasdiqlash kodingiz: {code}")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)

# --- 1. REGISTER ---
# --- 1. REGISTER ---
@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def register_page(request: Request, error: Optional[str] = None): # error qo'shildi
    return templates.TemplateResponse(request, "register.html", {"request": request, "error": error})

@app.post("/register")
async def register(email: str = Form(...), fullname: str = Form(...), password: str = Form(...), 
                   business_type: str = Form(...), business_name: str = Form(...)):
    code = str(random.randint(100000, 999999))
    temp_reg_data[email] = {
        "code": code, 
        "info": {"fullname": fullname, "email": email, "password": password, 
                 "business_type": business_type, "business_name": business_name}
    }
    send_otp(email, code)
    # URL orqali emailni uzatamiz, aks holda keyingi sahifa kimni tasdiqlashni bilmaydi
    return RedirectResponse(url=f"/verify?email={email}", status_code=303)

# --- 2. VERIFY ---
@app.get("/verify", response_class=HTMLResponse)
async def verify_page(request: Request, email: str): # email majburiy
    return templates.TemplateResponse(request, "verify.html", {"request": request, "email": email})

@app.post("/confirm")
async def confirm(email: str = Form(...), code: str = Form(...), db: Session = Depends(get_db)):
    print(f"Kelgan email: {email}") # Terminalda ko'rinadi
    print(f"Mavjud ma'lumotlar: {temp_reg_data.keys()}") # Lug'atdagi emaillar
    
    if email in temp_reg_data:
        if temp_reg_data[email]["code"] == code:
            new_user = models.User(**temp_reg_data[email]["info"])
            db.add(new_user)
            db.commit()
            return RedirectResponse(url="/login", status_code=303)
        else:
            return "Xato kod kiritildi"
    return "Email ro'yxatda topilmadi (Server qayta yongan bo'lishi mumkin)"

# --- 3. LOGIN ---
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse(request, "login.html", {"request": request, "error": error})

@app.post("/login")
async def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email, models.User.password == password).first()
    if not user: 
        return RedirectResponse(url="/login?error=1", status_code=303)
    return RedirectResponse(url=f"/dashboard?email={email}", status_code=303)

# --- 4. DASHBOARD ---



# main.py faylining 126-qatori atrofini quyidagicha o'zgartiring:

@app.get("/dashboard")
async def get_dashboard(request: Request, email: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return RedirectResponse(url="/login")

    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. Grafik uchun ma'lumotlarni birinchi bo'lib yig'amiz
    chart_labels = []
    chart_data = []
    stats = {}
    
    # Oxirgi 7 kunni hisoblaymiz
    for i in range(6, -1, -1):
        day = today_start - timedelta(days=i)
        next_day = day + timedelta(days=1)
        chart_labels.append(day.strftime("%d-%b"))
        
        # Har bir kun uchun foydani bazadan olamiz
        day_profit = db.query(func.sum(models.Sale.profit)).filter(
            models.Sale.user_email == email,
            models.Sale.created_at >= day,
            models.Sale.created_at < next_day
        ).scalar() or 0
        chart_data.append(float(day_profit))
    # main.py ichida get_dashboard funksiyasiga qo'shing:

# Eng ko'p sotilgan tovarlarni aniqlash (Top 5)
    top_sales = db.query(
        models.Sale.product_name, 
        func.sum(models.Sale.quantity).label('total_qty')
    ).filter(models.Sale.user_email == email)\
    .group_by(models.Sale.product_name)\
    .order_by(desc('total_qty'))\
    .limit(5).all()

    stats["top_products_labels"] = [item[0] for item in top_sales]
    stats["top_products_data"] = [float(item[1]) for item in top_sales]

    # 2. Boshqa hisob-kitoblar
    # Kassa = (Sotuvlar + Qarz to'lovlari) - Xarajatlar
    total_sales = db.query(func.sum(models.Sale.sell_price)).filter(models.Sale.user_email == email).scalar() or 0
    total_debt_payments = db.query(func.sum(models.DebtPayment.pay_amount)).join(models.Debt).filter(models.Debt.user_email == email).scalar() or 0
    
    # Xarajatlar jadvalingiz bor bo'lsa
    total_expenses = 0
    if hasattr(models, 'Expense'):
        total_expenses = db.query(func.sum(models.Expense.amount)).filter(models.Expense.email == email).scalar() or 0

    # 3. Stats lug'atini endi shakllantiramiz (o'zgaruvchilar yuqorida aniqlandi)
    stats = {
        "today_profit": chart_data[-1], # Endi chart_data aniqlangan
        "week_profit": sum(chart_data),
        "month_profit": db.query(func.sum(models.Sale.profit)).filter(
            models.Sale.user_email == email,
            models.Sale.created_at >= (today_start - timedelta(days=30))
        ).scalar() or 0,
        "kassa": (total_sales + total_debt_payments) - total_expenses,
        "active_debts": db.query(func.sum(models.Debt.remaining_amount)).filter(models.Debt.user_email == email).scalar() or 0,
        "chart_labels": chart_labels,
        "chart_data": chart_data
    }

    return templates.TemplateResponse(request, "dashboard.html", {"request": request, "user": user, "stats": stats})

@app.post("/add_product")
async def add_product(name: str = Form(...), category: str = Form(...), quantity: int = Form(...), 
                      price: float = Form(...), store: str = Form(...), email: str = Form(...), db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.name == name, models.Product.user_email == email).first()
    if not product:
        product = models.Product(name=name, category=category, user_email=email)
        db.add(product); db.commit(); db.refresh(product)
    
    db.add(models.ProductBatch(product_id=product.id, quantity=quantity, entry_price=price, store_name=store))
    db.commit()
    return RedirectResponse(url=f"/inventory?email={email}", status_code=303)




# --- 2. KEYIN UMUMIY SAHIFALARNI (GET) YOZING ---

@app.get("/{page}")
async def pages(page: str, request: Request, email: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user: return RedirectResponse(url="/login")
    
    context = {"request": request, "user": user}
    if page == "inventory":
        context["products"] = db.query(models.Product).filter(models.Product.user_email == email).all()
    elif page == "debts":
        # 1. Qarzlar ro'yxatini olish
        context["debts"] = db.query(models.Debt).filter(models.Debt.user_email == email).all()
        
        # 2. TO'G'IRLASH: Qarz yozishda tovarlarni tanlash uchun mahsulotlarni ham yuklash kerak
        context["products"] = db.query(models.Product).filter(models.Product.user_email == email).all()
        
    return templates.TemplateResponse(request, f"{page}.html", context)
# main.py ichiga qo'shing yoki yangilang
# Settings va Billing sahifalari uchun
@app.get("/settings")
async def settings_page(request: Request, email: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    return templates.TemplateResponse(request, "settings.html", {"request": request, "user": user, "email": email})

@app.get("/billing")
async def billing_page(request: Request, email: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    return templates.TemplateResponse(request, "billing.html", {"request": request, "user": user, "email": email})

@app.post("/sell_product")
async def sell_product(
    email: str = Form(...),
    product_name: str = Form(...),
    quantity_to_sell: int = Form(...),
    sell_price: float = Form(...),
    db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(
        models.Product.name == product_name, 
        models.Product.user_email == email
    ).first()

    if not product: return "Xato: Tovar topilmadi"

    batches = db.query(models.ProductBatch).filter(
        models.ProductBatch.product_id == product.id
    ).order_by(models.ProductBatch.id.asc()).all()

    total_available = sum(b.quantity for b in batches)
    if total_available < quantity_to_sell:
        return f"Xato: Yetarli tovar yo'q! (Mavjud: {total_available})"

    remaining_to_sell = quantity_to_sell
    total_buy_cost = 0  # Sotilgan tovarlarning tannarxi

    for batch in batches:
        if remaining_to_sell <= 0: break
        
        take_qty = min(batch.quantity, remaining_to_sell)
        total_buy_cost += take_qty * batch.entry_price # Tannarxni hisoblash
        
        batch.quantity -= take_qty
        remaining_to_sell -= take_qty
        
        if batch.quantity == 0:
            db.delete(batch)

    # --- TARIXGA SAQLASH (Sotuvlar jadvaliga) ---
    actual_profit = (sell_price * quantity_to_sell) - total_buy_cost
    new_sale = models.Sale(
        user_email=email,
        product_name=product_name,
        quantity=quantity_to_sell,
        sell_price=sell_price,
        buy_price=total_buy_cost / quantity_to_sell, # O'rtacha tannarxi
        profit=actual_profit
    )
    db.add(new_sale)
    db.commit()

    return RedirectResponse(url=f"/inventory?email={email}", status_code=303)

@app.post("/give_on_debt")
async def give_on_debt(
    email: str = Form(...),
    customer_name: str = Form(...),
    phone: str = Form(...),
    product_name: str = Form(...),
    quantity: int = Form(...),
    sell_price: float = Form(...),
    db: Session = Depends(get_db)
):
    # 1. Omborda tovar borligini tekshirish
    product = db.query(models.Product).filter(models.Product.name == product_name, models.Product.user_email == email).first()
    if not product: return "Tovar topilmadi"

    batches = db.query(models.ProductBatch).filter(models.ProductBatch.product_id == product.id).order_by(models.ProductBatch.id.asc()).all()
    
    total_available = sum(b.quantity for b in batches)
    if total_available < quantity: return "Omborda yetarli tovar yo'q"

    # 2. FIFO bo'yicha ombordan ayirish
    remaining_to_give = quantity
    for batch in batches:
        if remaining_to_give <= 0: break
        take = min(batch.quantity, remaining_to_give)
        batch.quantity -= take
        remaining_to_give -= take
        if batch.quantity == 0: db.delete(batch)

    # 3. Qarzni shakllantirish
    total_debt_sum = quantity * sell_price
    new_debt = models.Debt(
        user_email=email,
        customer_name=customer_name,
        phone=phone,
        product_name=product_name,
        quantity=quantity,
        total_amount=total_debt_sum,
        remaining_amount=total_debt_sum
    )
    db.add(new_debt)
    db.commit()
    return RedirectResponse(url=f"/debts?email={email}", status_code=303)

@app.post("/pay_debt")
async def pay_debt(
    debt_id: int = Form(...),
    pay_amount: float = Form(...),
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    # Qarzni olish
    debt = db.query(models.Debt).filter(models.Debt.id == debt_id, models.Debt.user_email == email).first()
    
    if not debt:
        return "Qarz topilmadi"

    # Yangi to'lovni hisoblaymiz
    debt.remaining_amount -= pay_amount

    # Agar qarz to'liq uzilgan bo'lsa (yoki ortig'i bilan)
    if debt.remaining_amount <= 0:
        db.delete(debt) # Qarzni o'chirish
        db.commit()
    else:
        # To'lovlar tarixiga qo'shish (agar sizda Payment modeli bo'lsa)
        new_payment = models.Payment(
            debt_id=debt.id,
            pay_amount=pay_amount,
            # pay_date avtomatik olinadi
        )
        db.add(new_payment)
        db.commit()

    return RedirectResponse(url=f"/debts?email={email}", status_code=303)

from fastapi import FastAPI, Form, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
# O'z loyihangizdagi model va bazaga ulanish funksiyalarini import qiling
# from models import Expense, User 
# from database import get_db

@app.post("/add_expense")
async def add_expense(
    email: str = Form(...),
    category: str = Form(...),
    amount: float = Form(...),
    db: Session = Depends(get_db)
):
    # 1. Xarajatni bazaga saqlash
    new_expense = Expense(email=email, category=category, amount=amount)
    db.add(new_expense)
    
    # 2. Kassadan pulni ayirish (Ixtiyoriy: Agar kassa statikasi bo'lsa)
    # user_stats = db.query(UserStats).filter(UserStats.email == email).first()
    # if user_stats:
    #     user_stats.kassa -= amount
    
    db.commit()
    return RedirectResponse(url=f"/billing?email={email}", status_code=303)

@app.post("/delete_expense")
async def delete_expense(
    id: int = Form(...),
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    expense = db.query(Expense).filter(Expense.id == id).first()
    if expense:
        db.delete(expense)
        db.commit()
    return RedirectResponse(url=f"/billing?email={email}", status_code=303)

@app.post("/delete_debt")
async def delete_debt(
    debt_id: int = Form(...), 
    email: str = Form(...), 
    db: Session = Depends(get_db)
):
    # Qarzni bazadan qidiramiz
    debt = db.query(models.Debt).filter(models.Debt.id == debt_id, models.Debt.user_email == email).first()
    
    if debt:
        db.delete(debt)
        db.commit()
    
    return RedirectResponse(url=f"/debts?email={email}", status_code=303)

# --- CHAT TARIXINI OLISH ---
@app.get("/chat-history")
async def get_chat_history(email: str, db: Session = Depends(get_db)):
    from models import ChatHistory  # Model nomingizga qarab o'zgartiring
    
    history = db.query(ChatHistory).filter(ChatHistory.email == email).all()
    
    # Ma'lumotlarni JSON formatiga o'tkazamiz
    return [
        {
            "role": h.role,
            "content": h.content,
            "image": h.image_url if hasattr(h, 'image_url') else None
        } for h in history
    ]

# --- ASOSIY AI ENDPOINT (VISION VA HISTORY BILAN) ---
@app.post("/ask-ai")
async def ask_ai(
    query: str = Form(...), 
    email: str = Form(...), 
    image: UploadFile = File(None), 
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user: return {"answer": "Foydalanuvchi topilmadi."}
    
    # 1. Sessiyani topish yoki yaratish
    session = db.query(models.ChatSession).filter(models.ChatSession.user_id == user.id).first()
    if not session:
        session = models.ChatSession(user_id=user.id, title="Yangi suhbat")
        db.add(session); db.commit(); db.refresh(session)

    # 2. Chat tarixini yig'ish (Oxirgi 10 ta xabar AI tushunishi uchun)
    history_msgs = db.query(models.ChatMessage).filter(models.ChatMessage.session_id == session.id)\
                     .order_by(models.ChatMessage.id.desc()).limit(10).all()
    chat_history = [{"role": m.role, "content": m.content} for m in reversed(history_msgs)]

    # 3. Biznes kontekstni tayyorlash
    active_debts = db.query(models.Debt).filter(models.Debt.user_email == email).all()
    debt_context = ", ".join([f"{d.customer_name}: {d.remaining_amount}" for d in active_debts])
    context = f"Mavjud qarzlar: {debt_context}"

    # 4. Rasmni saqlash (agar bo'lsa)
    image_url = None
    if image and image.filename:
        file_ext = image.filename.split(".")[-1]
        file_name = f"{uuid.uuid4()}.{file_ext}"
        image_path = os.path.join(UPLOAD_DIR, file_name)
        with open(image_path, "wb") as f:
            f.write(await image.read())
        image_url = f"/uploads/{file_name}" # Brauzer ko'rishi uchun URL

    # 5. AIga yuborish (Tarix va rasm yo'li bilan)
    # Eslatma: image_path bu yerda local yo'l bo'lishi kerak, shuning uchun local_path ni yuboramiz
    local_image_path = os.path.join(UPLOAD_DIR, file_name) if image_url else None
    ai_res = get_ai_response(query, context, chat_history=chat_history, image_path=local_image_path)

    ai_final_content = ""
    res_type = ai_res["type"]

    # 6. Tool Call mantiqini bajarish
    if res_type == "tool_call":
        for call in ai_res["calls"]:
            func_name = call.function.name
            args = json.loads(call.function.arguments)
            try:
                if func_name == "sell_product":
                    await sell_product(email=email, product_name=args['product_name'], 
                                       quantity_to_sell=int(args['quantity']), 
                                       sell_price=float(args['sell_price']), db=db)
                    ai_final_content += f"✅ {args['product_name']} sotildi. "
                
                elif func_name == "add_product_to_stock":
                    await add_product(name=args['name'], category=args.get('category', 'Boshqa'), 
                                      quantity=int(args['quantity']), price=float(args['price']), 
                                      store="Asosiy", email=email, db=db)
                    ai_final_content += f"✅ {args['name']} omborga qo'shildi. "
                
                elif func_name == "add_debt":
                    await give_on_debt(email=email, customer_name=args['customer_name'], 
                                       phone=args['phone'], product_name=args['product_name'], 
                                       quantity=int(args['quantity']), 
                                       sell_price=float(args['sell_price']), db=db)
                    ai_final_content += f"✅ {args['customer_name']}ga qarz yozildi. "
                
                elif func_name == "pay_debt":
                    debt = db.query(models.Debt).filter(models.Debt.customer_name.ilike(args['customer_name']), 
                                                        models.Debt.user_email == email).first()
                    if debt:
                        await pay_debt(debt_id=debt.id, pay_amount=float(args['amount']), email=email, db=db)
                        ai_final_content += f"✅ {args['customer_name']} to'lovi qabul qilindi. "
            except Exception as e:
                ai_final_content += f"❌ Xatolik: {str(e)}"
    else:
        ai_final_content = ai_res["content"]

    # 7. Xabarlarni bazaga saqlash
    db.add(models.ChatMessage(session_id=session.id, role="user", content=query, image_url=image_url))
    db.add(models.ChatMessage(session_id=session.id, role="assistant", content=ai_final_content))
    db.commit()

    return {"answer": ai_final_content, "type": res_type}
