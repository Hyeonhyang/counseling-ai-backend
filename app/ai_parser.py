"""AI Parser - Groq(Llama) 또는 Gemini를 이용한 상담 일지 분석"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER = os.getenv("AI_PROVIDER", "groq")  # "groq" or "gemini"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def _call_llm(prompt: str) -> str:
    """AI 모델 호출 (Groq 또는 Gemini)"""
    if AI_PROVIDER == "groq":
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()
    else:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        return response.text.strip()


def parse_counseling_text(text: str) -> dict:
    """상담 일지 텍스트를 분석하여 구조화된 데이터 추출"""
    try:
        prompt = f"""다음 상담 일지를 분석하여 아래 JSON 형식으로만 응답하세요. 다른 텍스트 없이 JSON만 출력하세요.
모든 텍스트 값은 반드시 한국어로 작성하세요. 절대 일본어, 중국어, 영어를 사용하지 마세요.

상담 일지:
\"\"\"
{text}
\"\"\"

출력 JSON 형식:
{{
  "depression_score": (0~100 사이 정수, 우울 수준. 반드시 1단위로 세밀하게 평가할 것. 예: 37, 62, 83처럼 정밀하게),
  "anxiety_score": (0~100 사이 정수, 불안 수준. 10단위 반올림 금지. 예: 44, 71, 28처럼 정밀하게),
  "anger_score": (0~100 사이 정수, 분노 수준. 정밀 평가 필수. 예: 15, 53, 67처럼),
  "self_esteem_score": (0~100 사이 정수, 자존감 수준. 높을수록 자존감 높음. 정밀 평가 필수. 예: 42, 58, 73처럼),
  "key_persons": ["핵심 언급 인물들 - 한국어로"],
  "defense_mechanisms": ["관찰된 방어기제나 심리 상태 - 한국어로"],
  "summary": "이 회차 상담의 핵심 내용을 한국어로 2~3문장으로 요약. 반드시 한국어만 사용할 것."
}}"""
        response_text = _call_llm(prompt)


        # JSON 블록 추출
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        result = json.loads(response_text.strip())
        return result

    except Exception as e:
        print(f"AI Parse Error: {e}")
        return _fallback_parse(text)


def generate_comparison_insight(sessions_data: list) -> str:
    """다중 세션 비교 인사이트 생성"""
    try:
        sessions_text = json.dumps(sessions_data, ensure_ascii=False, indent=2)
        prompt = f"""다음은 한 내담자의 여러 회차 상담 데이터입니다. 시간 흐름에 따른 변화를 분석하여 3줄 이내로 핵심 인사이트를 한국어로 작성하세요.

데이터:
{sessions_text}

형식: 변화 추이와 핵심 해석을 담은 전문적이고 간결한 분석 (3줄 이내)"""

        return _call_llm(prompt)

    except Exception as e:
        print(f"AI Insight Error: {e}")
        if sessions_data and len(sessions_data) >= 2:
            first = sessions_data[0]
            last = sessions_data[-1]
            dep_change = first["depression"] - last["depression"]
            anx_change = first["anxiety"] - last["anxiety"]
            est_change = last["self_esteem"] - first["self_esteem"]
            return (
                f"[자동 분석] {first['session_number']}회차 → {last['session_number']}회차: "
                f"우울 {'감소' if dep_change > 0 else '증가'} {abs(dep_change):.0f}점, "
                f"불안 {'감소' if anx_change > 0 else '증가'} {abs(anx_change):.0f}점, "
                f"자존감 {'상승' if est_change > 0 else '하락'} {abs(est_change):.0f}점."
            )
        return "AI 인사이트를 생성할 수 없습니다."


# ========== 위기 키워드 감지 (2-Step Filter) ==========

# 1단계: 주의 레벨 (Warning) 키워드
WARNING_KEYWORDS = [
    "사라지고 싶", "의미 없", "소용없", "포기하고 싶", "끝내고 싶", "지쳐", "다 내려놓",
    "아무도 없", "혼자", "버려진", "방에서 안 나", "연락 끊",
    "내 잘못", "나 때문", "민폐", "쓸모없", "한심", "태어나지 말았",
    "사라지면", "없어지면", "살기 싫", "힘들어서 못",
]

# 2단계: 위기 레벨 (Crisis) 직접 키워드
CRISIS_KEYWORDS_DIRECT = [
    "죽고 싶", "죽어야", "자해", "손목 긋", "번개탄", "음독", "수면제 모",
    "뛰어내리", "유서", "목 매", "목매", "죽을 거", "죽겠",
    "죽여버리", "칼로 찌르", "불 지르", "보복", "가만 안 두",
    "죽을래", "안 깨어나", "영원히 잠",
]

# 2단계: 위기 레벨 복합 문맥 키워드 (두 조건 동시 충족 필요)
CRISIS_CONTEXT_PAIRS = [
    (["정리", "신변", "재산"], ["물건", "주변", "다 끝", "다 정리"]),
    (["마지막", "그동안"], ["인사", "고마웠", "잘 지내", "안녕"]),
    (["아끼던", "나의 것", "내 물건"], ["주다", "나눠주", "버리"]),
]


def detect_risk_level(text: str) -> dict:
    """
    2-Step 위기 키워드 감지
    Returns: {"level": "none"|"warning"|"crisis", "keywords": [...], "requires_llm_check": bool}
    """
    detected_keywords = []
    level = "none"
    requires_llm = False

    # Step 1: Crisis 직접 키워드 검사 (가장 높은 우선순위)
    for keyword in CRISIS_KEYWORDS_DIRECT:
        if keyword in text:
            detected_keywords.append(keyword)
            level = "crisis"

    # Crisis 복합 문맥 검사
    if level != "crisis":
        for group_a, group_b in CRISIS_CONTEXT_PAIRS:
            a_found = [k for k in group_a if k in text]
            b_found = [k for k in group_b if k in text]
            if a_found and b_found:
                detected_keywords.extend(a_found)
                detected_keywords.extend(b_found)
                level = "crisis"
                requires_llm = True  # 복합 문맥은 LLM 검증 권장
                break

    # Step 2: Warning 키워드 검사 (Crisis가 아닌 경우)
    if level != "crisis":
        for keyword in WARNING_KEYWORDS:
            if keyword in text:
                detected_keywords.append(keyword)
                if level != "warning":
                    level = "warning"

    # LLM 2차 검증 (복합 문맥이 걸렸을 때만)
    if requires_llm and GROQ_API_KEY:
        try:
            llm_result = _verify_crisis_with_llm(text, detected_keywords)
            if llm_result == "low":
                level = "warning"  # 일상 표현으로 판단 → 위기에서 주의로 하향
        except:
            pass  # LLM 실패 시 보수적으로 crisis 유지

    return {
        "level": level,
        "keywords": list(set(detected_keywords)),
        "requires_llm_check": requires_llm,
    }


def _verify_crisis_with_llm(text: str, keywords: list) -> str:
    """LLM으로 복합 문맥 2차 검증"""
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)

    prompt = f"""다음 상담 내용에서 감지된 키워드: {keywords}

상담 내용:
\"\"\"{text}\"\"\"

이 키워드가 사용된 맥락을 판단해주세요.
- "crisis": 자살/자해 의도, 신변정리, 마지막 작별 등 위기 상황
- "low": 일상적인 정리, 일반적인 인사, 단순 비유적 표현

한 단어로만 답하세요: crisis 또는 low"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=10,
    )
    result = response.choices[0].message.content.strip().lower()
    return "low" if "low" in result else "crisis"


def generate_soap_note(text: str) -> dict:
    """상담 일지 텍스트를 SOAP 형식으로 자동 초안 생성"""
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)

        prompt = f"""당신은 정신건강 상담 기록 전문가입니다. 다음 상담 내용을 SOAP 형식으로 정리해주세요.
모든 내용은 반드시 한국어로만 작성하세요. 일본어, 중국어, 영어를 절대 사용하지 마세요.

상담 내용:
\"\"\"
{text}
\"\"\"

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트 없이 JSON만 출력하세요.

{{
  "subjective": "내담자가 직접 보고한 주관적 호소 내용. 한국어 2~4문장",
  "objective": "상담사가 관찰한 객관적 사항. 한국어 2~3문장",
  "assessment": "상담사의 전문적 평가. 한국어 2~3문장",
  "plan": "향후 상담 계획. 한국어 2~3문장"
}}"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800,
        )
        response_text = response.choices[0].message.content.strip()

        # JSON 블록 추출
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        result = json.loads(response_text.strip())
        return result

    except Exception as e:
        print(f"SOAP Generation Error: {e}")
        return {
            "subjective": "(AI 생성 실패 - 내담자의 주관적 호소를 여기에 작성해주세요)",
            "objective": "(AI 생성 실패 - 관찰된 객관적 사항을 여기에 작성해주세요)",
            "assessment": "(AI 생성 실패 - 전문적 평가를 여기에 작성해주세요)",
            "plan": "(AI 생성 실패 - 향후 계획을 여기에 작성해주세요)",
        }


def generate_rag_suggestion(current_state: dict, similar_cases: list) -> str:
    """유사 케이스 기반 대안 제안 생성"""
    try:
        prompt = f"""당신은 심리상담 수퍼바이저입니다. 현재 내담자의 상태와 유사한 과거 성공 사례를 바탕으로 대안 기법을 추천하세요.

현재 내담자 상태:
{json.dumps(current_state, ensure_ascii=False)}

유사 과거 성공 사례:
{json.dumps(similar_cases, ensure_ascii=False)}

형식: 구체적인 기법 전환 제안을 3~4문장으로 한국어로 작성하세요. 근거를 포함하세요."""

        return _call_llm(prompt)

    except Exception as e:
        print(f"AI RAG Error: {e}")
        if similar_cases:
            techniques = [c.get("technique_used", "") for c in similar_cases if c.get("technique_used")]
            current_tech = current_state.get("technique", "")
            alt_techniques = [t for t in techniques if t != current_tech and t != "미기록"]
            if alt_techniques:
                return (
                    f"[자동 추천] 유사 케이스에서 사용된 기법: {', '.join(set(alt_techniques))}. "
                    f"현재 기법({current_tech or '미기록'})의 효과가 정체되었다면 "
                    f"'{alt_techniques[0]}' 기법 전환을 고려해보세요."
                )
        return "AI 추천을 생성할 수 없습니다."


def _fallback_parse(text: str) -> dict:
    """AI 실패 시 키워드 기반 fallback"""
    depression_keywords = ["우울", "슬프", "무기력", "의욕", "눈물", "죽고싶"]
    anxiety_keywords = ["불안", "걱정", "초조", "긴장", "두려", "공포"]
    anger_keywords = ["분노", "화가", "짜증", "열받", "억울"]
    esteem_keywords = ["자신감", "자존", "능력", "가치", "잘할"]

    dep = min(100, sum(10 for k in depression_keywords if k in text))
    anx = min(100, sum(10 for k in anxiety_keywords if k in text))
    ang = min(100, sum(10 for k in anger_keywords if k in text))
    est = max(0, 70 - dep // 2)

    return {
        "depression_score": dep,
        "anxiety_score": anx,
        "anger_score": ang,
        "self_esteem_score": est,
        "key_persons": [],
        "defense_mechanisms": [],
        "summary": "(AI 분석 실패 - 키워드 기반 fallback 결과)",
    }
