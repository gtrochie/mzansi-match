from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="Mzansi Match API")

# Allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to Supabase
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)


# ── MODELS ──────────────────────────────────────────────

class UserProfile(BaseModel):
    name: str
    gender: Optional[str] = None
    city: Optional[str] = None
    culture: Optional[str] = None
    religion: Optional[str] = None


class AnswerSet(BaseModel):
    want_kids: Optional[int] = None
    intention: Optional[int] = None
    monogamy: Optional[int] = None
    man_cheat: Optional[int] = None
    marriage: Optional[int] = None
    have_kids: Optional[int] = None
    allowance: Optional[int] = None
    money: Optional[int] = None
    public_private: Optional[int] = None
    family_inv: Optional[int] = None
    loyalty: Optional[int] = None
    rel_imp: Optional[int] = None
    traditional: Optional[int] = None
    gender_roles: Optional[int] = None
    financial_lead: Optional[int] = None


class SubmitQuizRequest(BaseModel):
    user_a: UserProfile
    user_b: UserProfile
    answers_a: AnswerSet
    answers_b: AnswerSet
    score: int
    dealbreaker_hit: bool
    dealbreaker_question: Optional[str] = None
    values_pct: int
    lifestyle_pct: int
    relationship_pct: int
    faith_pct: int
    power_pct: int


# ── ROUTES ──────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "Mzansi Match API is live ♥"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/quiz/submit")
async def submit_quiz(data: SubmitQuizRequest):
    try:
        # Save User A
        user_a_res = supabase.table("users").insert({
            "name": data.user_a.name,
            "gender": data.user_a.gender,
            "city": data.user_a.city,
            "culture": data.user_a.culture,
            "religion": data.user_a.religion,
        }).execute()
        user_a_id = user_a_res.data[0]["id"]

        # Save User B
        user_b_res = supabase.table("users").insert({
            "name": data.user_b.name,
            "gender": data.user_b.gender,
            "city": data.user_b.city,
            "culture": data.user_b.culture,
            "religion": data.user_b.religion,
        }).execute()
        user_b_id = user_b_res.data[0]["id"]

        # Save session
        session_res = supabase.table("sessions").insert({
            "user_a_id": user_a_id,
            "user_b_id": user_b_id,
            "score": data.score,
            "dealbreaker_hit": data.dealbreaker_hit,
            "dealbreaker_question": data.dealbreaker_question,
            "values_pct": data.values_pct,
            "lifestyle_pct": data.lifestyle_pct,
            "relationship_pct": data.relationship_pct,
            "faith_pct": data.faith_pct,
            "power_pct": data.power_pct,
        }).execute()
        session_id = session_res.data[0]["id"]

        # Save answers for User A
        answers_a = data.answers_a.model_dump()
        for qid, val in answers_a.items():
            if val is not None:
                supabase.table("answers").insert({
                    "session_id": session_id,
                    "user_id": user_a_id,
                    "question_id": qid,
                    "answer_value": val,
                }).execute()

        # Save answers for User B
        answers_b = data.answers_b.model_dump()
        for qid, val in answers_b.items():
            if val is not None:
                supabase.table("answers").insert({
                    "session_id": session_id,
                    "user_id": user_b_id,
                    "question_id": qid,
                    "answer_value": val,
                }).execute()

        return {
            "success": True,
            "session_id": session_id,
            "score": data.score,
            "message": "Quiz results saved successfully ♥"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Admin endpoint — basic platform stats"""
    try:
        sessions = supabase.table("sessions").select("*").execute()
        users = supabase.table("users").select("*").execute()
        all_sessions = sessions.data

        total = len(all_sessions)
        if total == 0:
            return {"total_sessions": 0, "average_score": 0, "dealbreaker_rate": 0}

        avg_score = round(sum(s["score"] for s in all_sessions) / total)
        dealbreakers = sum(1 for s in all_sessions if s["dealbreaker_hit"])
        db_rate = round((dealbreakers / total) * 100)

        scores = [s["score"] for s in all_sessions if not s["dealbreaker_hit"]]
        high = sum(1 for s in scores if s >= 75)
        mid = sum(1 for s in scores if 45 <= s < 75)
        low = sum(1 for s in scores if s < 45)

        return {
            "total_sessions": total,
            "total_users": len(users.data),
            "average_score": avg_score,
            "dealbreaker_rate_pct": db_rate,
            "high_compatibility": high,
            "mid_compatibility": mid,
            "low_compatibility": low,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions")
async def get_sessions():
    """Admin endpoint — list all sessions"""
    try:
        res = supabase.table("sessions").select("*").order("created_at", desc=True).limit(50).execute()
        return {"sessions": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
