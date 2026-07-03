"""100명 내담자 + 각 5~20회차 모의 상담 데이터 생성"""
import random
import json
from datetime import datetime, timedelta
from app.database import SessionLocal, engine
from app.models import Base, Client, Session
from app.models import Counselor
from app.auth import hash_password

# 이름 풀
LAST_NAMES = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임", "한", "오", "서", "신", "권", "황", "안", "송", "류", "홍"]
FIRST_NAMES_M = ["민준", "서준", "도윤", "예준", "시우", "하준", "주원", "지호", "지훈", "준서", "건우", "현우", "우진", "승현", "태민"]
FIRST_NAMES_F = ["서연", "서윤", "지우", "서현", "민서", "하은", "하윤", "윤서", "지민", "채원", "수아", "지아", "예은", "유진", "소희"]

ISSUES = [
    "직장 내 대인관계 갈등으로 인한 우울감",
    "완벽주의 성향으로 인한 만성 불안",
    "부모와의 갈등 및 분리불안",
    "이별 후 우울감과 자존감 저하",
    "학업 스트레스 및 시험 불안",
    "직장 내 번아웃 증후군",
    "사회불안장애 (대인기피)",
    "부부 갈등 및 의사소통 문제",
    "자존감 저하 및 자기비하 패턴",
    "분노조절 어려움",
    "트라우마 후 스트레스 장애 (PTSD)",
    "강박적 사고 패턴",
    "공황장애 및 광장공포증",
    "섭식장애 관련 심리적 요인",
    "진로 고민 및 정체성 혼란",
    "가족 내 역할 갈등 (장녀/장남 부담)",
    "만성 피로 및 무기력감",
    "대인관계에서의 경계설정 어려움",
    "애착 불안정으로 인한 관계 패턴",
    "상실감 및 애도 과정",
]

TECHNIQUES = ["CBT", "ACT", "정신역동", "EMDR", "DBT", "인간중심", "게슈탈트", "해결중심", "인지치료", "행동활성화"]

KEY_PERSONS_POOL = ["어머니", "아버지", "배우자", "상사", "동료", "친구", "형제", "자녀", "연인", "선생님", "시어머니"]

DEFENSE_MECHANISMS = ["합리화", "투사", "억압", "퇴행", "부정", "전치", "반동형성", "승화", "지성화", "회피", "분리", "해리"]

SAMPLE_TEXTS = [
    "오늘 내담자는 직장에서 상사와의 갈등에 대해 이야기했다. 상사가 회의 중 자신의 의견을 무시했다고 느꼈으며, 그 이후로 출근할 때마다 심한 불안감을 경험한다고 보고했다. '내가 무능한 것 같다'는 자동적 사고가 반복되고 있으며, 최근에는 회사에 가기 싫어서 아침에 일어나기가 힘들다고 했다.",
    "내담자는 어머니와의 관계에서 느끼는 죄책감에 대해 탐색했다. 어머니가 전화할 때마다 '네가 없으면 나는 어떡하니'라는 말을 듣는데, 이 말이 내담자에게 큰 부담으로 작용하고 있다. 독립하고 싶지만 어머니를 버리는 것 같은 죄책감이 든다고 했다.",
    "이번 회차에서 내담자는 지난주 있었던 발표 상황에 대해 이야기했다. 발표 전날 밤새 잠을 못 잤고, 발표 중에 손이 떨리고 목소리가 떨려서 중간에 멈춰야 했다고 보고했다. '모든 사람이 나를 이상하게 볼 것이다'라는 예기불안이 매우 강하다.",
    "내담자는 배우자와의 의사소통 문제에 대해 호소했다. 배우자가 자신의 감정을 무시한다고 느끼며, 대화를 시도해도 결국 싸움으로 번진다고 했다. 내담자는 '어차피 말해봤자 소용없다'는 무력감을 표현했으며, 점차 대화를 회피하는 패턴이 강화되고 있다.",
    "오늘 세션에서 내담자는 최근 업무량 증가로 인한 번아웃 증상을 보고했다. 주말에도 일을 하며, 취미 활동이나 친구 만남을 모두 포기했다고 했다. '쉬면 뒤처진다'는 생각이 강하고, 몸은 피곤한데 멈출 수가 없다고 표현했다. 수면의 질이 매우 저하되어 있다.",
    "내담자는 친구 관계에서 거절당하는 것에 대한 두려움을 탐색했다. 모임에서 자신이 말을 할 때 다른 사람들이 관심 없어 보이면 극도로 위축되며, 그 후 며칠간 그 장면을 반복적으로 떠올린다고 했다. 자존감이 매우 낮은 상태이다.",
    "내담자는 아버지의 사망 이후 경험하고 있는 애도 과정에 대해 이야기했다. 아직 실감이 나지 않는다고 하면서도, 때때로 갑자기 울컥하는 감정이 밀려온다고 보고했다. 아버지에게 하지 못한 말들에 대한 후회가 크다.",
    "이번 세션에서 내담자는 자해 충동에 대해 솔직하게 이야기했다. 스트레스가 극에 달하면 자해 충동이 올라오지만, 실행에 옮기지는 않았다고 보고했다. 감정 조절의 대안적 방법을 함께 탐색했다.",
    "내담자는 연인과 헤어진 후 3개월째 일상이 회복되지 않는다고 호소했다. 식욕이 없고, 잠을 못 자며, 모든 것이 의미 없게 느껴진다고 했다. '나는 사랑받을 자격이 없다'는 핵심 신념이 활성화되어 있다.",
    "오늘 내담자는 시어머니와의 갈등에서 느끼는 분노에 대해 표현했다. 시어머니가 양육 방식을 지속적으로 비판하며, 배우자는 중간에서 아무 말도 하지 않는다고 했다. 분노를 참다가 한 번씩 폭발하는 패턴이 반복되고 있다.",
]


def generate_session_text(issue: str, session_num: int, key_persons: list) -> str:
    """세션 번호와 이슈에 맞는 상담 일지 텍스트 생성"""
    base_text = random.choice(SAMPLE_TEXTS)
    # 약간의 변형
    additions = [
        f"\n\n내담자는 {random.choice(key_persons)}와의 관계에서 특히 스트레스를 받고 있다고 보고했다.",
        f"\n\n{session_num}회차 진행 중이며, 초기 대비 {'약간의 호전' if session_num > 5 else '여전히 어려움'}을 보이고 있다.",
        f"\n\n다음 세션에서는 {random.choice(['감정 일기 과제', '행동 활성화 계획', '인지 재구성 연습', '마음챙김 훈련'])}를 진행할 예정이다.",
    ]
    return base_text + random.choice(additions)


def generate_scores(session_num: int, total_sessions: int, issue_type: str) -> dict:
    """세션 진행에 따라 점수 변화 시뮬레이션"""
    # 초기 점수 (높은 증상)
    base_dep = random.randint(50, 85)
    base_anx = random.randint(45, 80)
    base_ang = random.randint(30, 70)
    base_est = random.randint(20, 45)

    # 진행에 따른 개선 (약간의 노이즈 포함)
    progress = session_num / max(total_sessions, 1)
    improvement = progress * random.uniform(0.3, 0.7)  # 30~70% 개선
    noise = random.randint(-8, 8)

    dep = max(5, int(base_dep * (1 - improvement) + noise))
    anx = max(5, int(base_anx * (1 - improvement) + noise))
    ang = max(5, int(base_ang * (1 - improvement * 0.8) + noise))
    est = min(95, int(base_est + (100 - base_est) * improvement * 0.6 + noise))

    return {
        "depression_score": min(100, dep),
        "anxiety_score": min(100, anx),
        "anger_score": min(100, ang),
        "self_esteem_score": max(5, est),
    }


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 이미 데이터 있으면 스킵
    if db.query(Client).count() >= 100:
        print("Already seeded (100+ clients exist).")
        db.close()
        return

    print("Seeding 100 clients with sessions...")

    # 데모 상담사 3명 생성
    counselors = [
        Counselor(email="kim@demo.com", password_hash=hash_password("1234"), name="김상담", license_type="임상심리전문가", organization="마음건강센터"),
        Counselor(email="lee@demo.com", password_hash=hash_password("1234"), name="이치료", license_type="상담심리사1급", organization="마음건강센터"),
        Counselor(email="park@demo.com", password_hash=hash_password("1234"), name="박심리", license_type="정신건강임상심리사", organization="행복클리닉"),
    ]
    db.add_all(counselors)
    db.flush()

    for i in range(100):
        gender = random.choice(["M", "F"])
        last = random.choice(LAST_NAMES)
        first = random.choice(FIRST_NAMES_M if gender == "M" else FIRST_NAMES_F)
        name = f"{last}{first}"
        age = random.randint(19, 55)
        issue = random.choice(ISSUES)

        client = Client(name=name, age=age, gender=gender, presenting_issue=issue, counselor_id=random.choice(counselors).id)
        db.add(client)
        db.flush()

        # 5~20 회차 세션 생성
        num_sessions = random.randint(5, 20)
        technique = random.choice(TECHNIQUES)
        key_persons = random.sample(KEY_PERSONS_POOL, k=random.randint(1, 3))
        defenses = random.sample(DEFENSE_MECHANISMS, k=random.randint(1, 3))

        start_date = datetime.now() - timedelta(days=num_sessions * 7)

        for s_num in range(1, num_sessions + 1):
            scores = generate_scores(s_num, num_sessions, issue)
            text = generate_session_text(issue, s_num, key_persons)
            session_date = start_date + timedelta(days=(s_num - 1) * 7)

            # 중간에 기법 전환 시뮬레이션 (30% 확률)
            if s_num > num_sessions // 2 and random.random() < 0.3:
                technique = random.choice([t for t in TECHNIQUES if t != technique])

            session = Session(
                client_id=client.id,
                session_number=s_num,
                raw_text=text,
                depression_score=scores["depression_score"],
                anxiety_score=scores["anxiety_score"],
                anger_score=scores["anger_score"],
                self_esteem_score=scores["self_esteem_score"],
                key_persons=json.dumps(key_persons, ensure_ascii=False),
                defense_mechanisms=json.dumps(defenses, ensure_ascii=False),
                ai_summary=f"{s_num}회차: {issue} 관련 상담 진행. {'초기 탐색' if s_num <= 3 else '중기 작업' if s_num <= num_sessions * 0.7 else '후기 정리'} 단계.",
                technique_used=technique,
                session_date=session_date,
            )
            db.add(session)

        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/100 clients created...")

    db.commit()
    db.close()
    print(f"Done! 100 clients seeded with sessions.")


if __name__ == "__main__":
    seed()
