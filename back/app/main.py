import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from fastapi.middleware.cors import CORSMiddleware
import openai
import asyncio

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai.api_key = "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"  # 환경변수에 API 키 설정

class SubmitRequest(BaseModel):
    email: EmailStr | None = None
    advice: str

class SubmitResponse(BaseModel):
    recommendation1: dict
    recommendation2: dict
    recommendation3: dict
    message: str

class FeedbackRequest(BaseModel):
    email: EmailStr
    advice: str

async def call_openai_api(prompt: str):
    try:
        response = await openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a computer hardware expert. You are required to recommend prebuilt PC. You wil recommend 3 and it's about best, balanced, and High-performance recommendation."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

@app.post("/submit", response_model=SubmitResponse)
async def submit_advice(data: SubmitRequest):
    if not data.advice.strip():
        raise HTTPException(status_code=400, detail="advice is required")

    prompt = (
        f"사용자가 다음과 같이 컴퓨터 구매 관련 조언을 요청했습니다:\n"
        f"'{data.advice}'\n"
        "이 사용자가 원하는 조건에 맞춰 CPU, GPU, RAM, 가격으로 구성된 3가지 추천 컴퓨터 사양을 아래 형식에 맞게 알려주세요. 다른 말은 하나도 넣지마. 제품은 조립형이 아닌 완제품만 추천해주세요. 가격은 한화로 10원 단위까지 세세하게, 쉼표없이 적어주세요.쇼핑몰의 경우 정확히 그 물건을 파는 주소와 함께 쿠팡, 지마켓 2개정도 적어주세요 적어주세요. 쇼핑몰은 {\"쿠팡\":\"www.as\"}입니다\n"
        "output form :[{\"추천\": \"\",\"장점\": \"[]\",\"단점\": \"[]\"\",\"쇼핑몰\": \"{},\"한줄평\": \"\",\"cpu\": \"\", \"gpu\": \"\", \"ram\": \"\", \"price\": 0},{\"가성비\": \"\",\"장점\": \"[]\",\"단점\": \"[]\",\"쇼핑몰\": \"{},\"한줄평\": \"\",cpu\": \"\", \"gpu\": \"\", \"ram\": \"\", \"price\": 0},{\"최저가\": \"\",\"장점\": \"[]\",\"단점\": \"[]\",\"쇼핑몰\": \"{},\"한줄평\": \"\",\"cpu\": \"\", \"gpu\": \"\", \"ram\": \"\", \"price\": 0}]"
    )

    result_text = await call_openai_api(prompt)

    try:
        # OpenAI가 JSON 형태로 응답한다고 가정하고 파싱 시도
        import json
        recommendations = json.loads(result_text)
        if not isinstance(recommendations, list) or len(recommendations) != 3:
            raise ValueError("잘못된 추천 데이터 형식")
    except Exception as e:
        # JSON 파싱 실패 시 예외 처리
        raise HTTPException(status_code=500, detail=f"AI 추천 데이터 파싱 실패: {str(e)}")

    return {
        "recommendation1": recommendations[0],
        "recommendation2": recommendations[1],
        "recommendation3": recommendations[2],
        "message": "AI 추천 결과입니다.",
    }

@app.post("/feedback")
async def receive_feedback(data: FeedbackRequest):
    print(f"[feedback] 이메일: {data.email}, 의견: {data.advice}")
    # TODO: DB 저장 또는 메일 전송 등 처리
    return {"message": "의견이 성공적으로 접수되었습니다."}

