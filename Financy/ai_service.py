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
    
    system_prompt = f"""Siz Financy.uz tizimining aqlli operatorisiz. 
    Biznes holati: {context_data}

    MUHIM QOIDALAR:
    1. QARZ: Agar foydalanuvchi qarzga mahsulot berilganini aytsa, lekin TELEFON RAQAMINI aytmagan bo'lsa, funksiyani chaqirmang! "Mijozning telefon raqami qanday?" deb so'rang.
    2. RAQAMLAR: 'quantity' integer, 'price'/'amount' float bo'lsin.
    3. TO'LOV: "Aziz qarzini uzdi" desa, 'pay_debt' chaqiring.
    4. TASVIR: Agar rasm kelsa, uni tahlil qiling va undagi mahsulotlar yoki cheklarni tushunishga harakat qiling.
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