import os
import requests
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI(title="DSNA SEO-AI Copilot")

# Разрешаем запросы с Tilda (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Разрешаем доступ откуда угодно (для тестов)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ТВОИ КЛЮЧИ API
GEMINI_API_KEY = "AIzaSyBGdzpisUj-PrAobyZUUduGMwnNMKfHqEE"
SERPER_API_KEY = "bc96834d0d585ceab12680d375737fcde6f4af34"
XMLRIVER_USER = "20434"
XMLRIVER_KEY = "01729268242056324e3166b11d5f055989dd96e7"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro')

class QueryRequest(BaseModel):
    keyword: str

def get_google_top(query: str):
    """Парсинг Google через Serper.dev"""
    url = "https://google.serper.dev/search"
    payload = {"q": query, "num": 10, "gl": "ru", "hl": "ru"}
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        results = response.json().get('organic', [])
        return "\n".join([f"Google: {item.get('title')} - {item.get('snippet')}" for item in results])
    except:
        return "Google: Ошибка или нет данных"

def get_yandex_top(query: str):
    """Парсинг Яндекса через XMLRiver"""
    url = f"http://xmlriver.com/search_yandex/json?user={XMLRIVER_USER}&key={XMLRIVER_KEY}&query={query}&lr=225"
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        if 'organic' not in data:
            return "Яндекс: нет данных"
            
        yandex_context = []
        for item in data['organic'][:10]:
            title = item.get('title', '')
            passage = item.get('passage', '')
            yandex_context.append(f"Yandex: {title} - {passage}")
        return "\n".join(yandex_context)
    except Exception as e:
        return f"Яндекс: Ошибка парсинга {str(e)}"

@app.post("/api/v1/analyze")
async def analyze_keyword(req: QueryRequest):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Собираем данные
    google_context = get_google_top(req.keyword)
    yandex_context = get_yandex_top(req.keyword)
    
    system_prompt = f"""
    Твоя роль: Senior AI-SEO аналитик и технический редактор.
    СИСТЕМНОЕ ВРЕМЯ НА ДАННЫЙ МОМЕНТ: {current_time}. 
    Это критически важно. Анализируй данные именно на эту дату.
    
    Задача: Провести анализ по запросу "{req.keyword}".
    
    Контекст из поисковиков (ТОП-10):
    {google_context}
    
    {yandex_context}
    
    Выдай ответ:
    1. Intent (Главная боль пользователя)
    2. Missing Gaps (О чем забыли конкуренты, каких данных за текущий год нет)
    3. SEO Structure (Оптимальная структура H2-H3)
    4. GEO Elements (Какие таблицы и маркированные списки добавить для AI Overviews)
    """
    
    response = model.generate_content(system_prompt)
    
    return {
        "timestamp": current_time,
        "keyword": req.keyword,
        "ai_result": response.text
    }