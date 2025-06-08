import os
import json
import urllib.parse
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import openai

def get_first_product_image(model_name: str) -> str:
    query = urllib.parse.quote(model_name)
    search_url = f"https://search.danawa.com/dsearch.php?query={query}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        res = requests.get(search_url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        img_tag = soup.select_one("div.thumb_image img")
        if img_tag:
            src = img_tag.get("data-original") or img_tag.get("src")
            if src and src.startswith("//"):
                src = "https:" + src
            return src or ""
        return ""
    except Exception as e:
        print(f"[이미지 로드 실패] {model_name}: {e}")
        return ""

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포시 도메인 명시 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai.api_key =  os.getenv("OPENAI_API_KEY")

class SubmitRequest(BaseModel):
    advice: str
    money: str



# PC 데이터 JSON 파일 읽기
try:
    with open("latest_pc_data.json", "r", encoding="utf-8") as f:
        pc_list = json.load(f)
except Exception as e:
    print(f"PC 데이터 로드 실패: {e}")
    pc_list = []

def filter_pcs(purpose: str, max_price: int):
    filtered = [
        pc for pc in pc_list
        if int(pc.get("가격", 0)) <= max_price and purpose.lower() in pc.get("용도", "").lower()
    ]
    if not filtered:
        filtered = [pc for pc in pc_list if int(pc.get("가격", 0)) <= max_price]
    return filtered

def create_prompt(filtered_pcs, purpose):
    pcs_summary = "\n".join(
        [f"- {pc.get('모델명', '모델명없음')}: 장점 {pc.get('장점', '없음')}, 단점 {pc.get('단점', '없음')}, 가격 {pc.get('가격', '0')}원"
         for pc in filtered_pcs]
    )
    prompt = f"""
다음은 2025년 최신 컴퓨터 후보 목록입니다:
{pcs_summary}

사용자의 용도는 '{purpose}' 입니다.
이 중에서 용도에 가장 적합한 컴퓨터를 추천해 주세요. outputform외의 것은 하나도 얘기하지 마세요.
output form :[
    {{"이름": "추천: 모델명", "장점": [], "단점": [], "price": 0}},
    {{"이름": "밸런스: 모델명", "장점": [], "단점": [], "price": 0}},
    {{"이름": "최고품질: 모델명", "장점": [], "단점": [], "price": 0}}
]
"""
    return prompt

async def get_recommendation(purpose: str, max_price: int):
    filtered = filter_pcs(purpose, max_price)
    prompt = create_prompt(filtered, purpose)
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant specializing in computer recommendations."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

@app.post("/submit")
async def submit_advice(data: SubmitRequest):
    if not data.advice.strip():
        raise HTTPException(status_code=400, detail="advice is required")

    try:
        max_price = int(data.money)
    except ValueError:
        raise HTTPException(status_code=400, detail="money는 숫자여야 합니다")

    result_text = await get_recommendation(data.advice, max_price)

    try:
        recommendations = json.loads(result_text)
        for a in range(3):
            url = get_first_product_image(recommendations[a].get("이름").split(":")[-1])
            recommendations[a]["image"] = url
        if not isinstance(recommendations, list) or len(recommendations) != 3:
            raise ValueError("잘못된 추천 데이터 형식")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 추천 데이터 파싱 실패: {str(e)}")
    print(recommendations)

    return recommendations
