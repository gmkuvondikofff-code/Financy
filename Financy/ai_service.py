from groq import Groq

client = Groq(api_key="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")

def get_ai_response(user_query, context_data):
    # System prompt o'zgarmadi, shunday qoldi
    system_prompt = f"""
    Siz Financy.uz tizimining aqlli tahlilchisisiz. 
    Foydalanuvchining biznes ma'lumotlari: {context_data}
    Faqat ushbu ma'lumotlarga tayanib suhbat quring. 
    Javoblaringiz aniq, professional va o'zbek tilida bo'lsin va shu turdagi biznes doirasida suhbatlashing.
    """
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ],
            # ESKI: "llama3-8b-8192" -> YANGI VA ISHLAYDIGAN:
            model="llama-3.3-70b-versatile",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        # Xatolik haqida batafsil ma'lumot (debug uchun foydali)
        return f"AI bilan bog'lanishda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring."