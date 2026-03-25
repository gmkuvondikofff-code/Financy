from groq import Groq
import json
import base64

# Groq API kalitini o'rnatamiz
client = Groq(api_key="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")

# AI foydalanishi mumkin bo'lgan asboblar (Tools)
tools = [
    {
        "type": "function",
        "function": {
            "name": "sell_product",
            "description": "Mahsulotni sotish amalini bajaradi",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string", "description": "Mahsulot nomi"},
                    "quantity": {"type": "integer", "description": "Soni"},
                    "sell_price": {"type": "number", "description": "Sotilgan narxi"}
                },
                "required": ["product_name", "quantity", "sell_price"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_product_to_stock",
            "description": "Omborga yangi mahsulot qo'shish yoki mavjudini ko'paytirish",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "price": {"type": "number", "description": "Kelgan narxi (tannarxi)"},
                    "category": {"type": "string"}
                },
                "required": ["name", "quantity", "price"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_debt",
            "description": "Mijozga qarzga mahsulot berish",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "product_name": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "sell_price": {"type": "number"},
                    "phone": {"type": "string", "description": "Mijoz telefon raqami"}
                },
                "required": ["customer_name", "product_name", "quantity", "sell_price", "phone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pay_debt",
            "description": "Mijoz qarzini to'laganda ishlatiladi",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "amount": {"type": "number", "description": "To'langan summa"}
                },
                "required": ["customer_name", "amount"]
            }
        }
    }
]

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_ai_response(user_query, context_data, chat_history=None, image_path=None):
    # Model tanlash: Rasm bo'lsa vision, bo'lmasa kuchliroq model
    model_name = "llama-3.2-11b-vision-preview" if image_path else "llama-3.3-70b-versatile"
    
    system_prompt = f"""Siz Financy.uz tizimining professional va qat'iy biznes-operatorisiz. Sizning vazifangiz — tadbirkorga savdo, qarz va ombor hisobini yuritishda yordam berish.
    Biznes holati: {context_data}

MUHIM KO'RSATMALAR (STRICT RULES):
1. SHAXSIYAT VA TON: Faqat biznes doirasida javob bering. Salom-alikdan so'ng darhol ishga o'ting. Lirik chekinishlar, falsafiy fikrlar yoki biznesga aloqador bo'lmagan maslahatlar qat'iyan man etiladi. Javoblar qisqa, aniq va lo'nda bo'lsin.
2. CHEKLOV: Agar foydalanuvchi biznesga aloqador bo'lmagan (siyosat, ob-havo, o'yin va h.k.) mavzularda gapirsa, xushmuomalalik bilan rad eting: "Kechirasiz, men faqat Financy.uz doirasidagi biznes amallari bo'yicha yordam bera olaman."
3. AMALLAR (TOOLS): 
   - Faqat foydalanuvchi aniq fakt (miqdor, narx, nom) aytsa, funksiyani chaqiring. 
   - Noaniq gaplar (masalan: "Sotuv bo'ldi") kelsa, funksiyani chaqirmang, aniqlashtiruvchi savol bering: "Qaysi mahsulotdan qancha sotildi?"
4. QARZ MANTIQI: Qarz yozish uchun 'Mijoz ismi', 'Mahsulot', 'Miqdor' va 'Telefon raqami' majburiy. Bittasi kam bo'lsa ham funksiyani ishlatmang, yetishmayotgan ma'lumotni so'rang.
5. TAHLIL: Foydalanuvchi tushum yoki foyda haqida so'rasa, yuqoridagi {context_data} dan foydalanib, aniq raqamlarni ayting. Taxmin qilmang.
6. TASVIRLAR: Agar rasm kelsa (cheklar, mahsulotlar), undagi matnlarni o'qing va faqat biznesga tegishli faktlarni (tovar nomi, narxi) ajratib ko'rsating.

Muloqot tili: O'zbek tili. 
Uslub: Minimalizm (kamroq matn, ko'proq natija).
"""
    

    messages = [{"role": "system", "content": system_prompt}]

    # Tarixni qo'shish
    if chat_history:
        for msg in chat_history:
            messages.append({"role": msg['role'], "content": msg['content']})

    # Hozirgi xabar (matn yoki rasm bilan)
    if image_path:
        base64_image = encode_image(image_path)
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": user_query},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                }
            ]
        })
    else:
        messages.append({"role": "user", "content": user_query})

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=tools if not image_path else None, # Visionda hozircha tools ishlamasligi mumkin
            tool_choice="auto" if not image_path else None
        )

        response_message = response.choices[0].message
        
        # Agar Tool chaqirilsa
        if response_message.tool_calls:
            return {"type": "tool_call", "calls": response_message.tool_calls}
        
        # Oddiy matn bo'lsa
        return {"type": "text", "content": response_message.content}

    except Exception as e:
        return {"type": "text", "content": f"AI bilan bog'lanishda xatolik: {str(e)}"}
