import streamlit as st
import pandas as pd
import os
from datetime import datetime
import json
from anthropic import Anthropic

# ==========================================
# 페이지 설정
# ==========================================
st.set_page_config(
    page_title="🎓 교과 세특 생성 플랫폼 v2.0",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 모던 디자인 (CSS)
# ==========================================
st.markdown("""
<style>
    /* 전체 폰트 & 배경 */
    .stApp {
        background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
    }
    
    /* 메인 제목 */
    h1 {
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
    }
    
    /* 소제목 */
    h2, h3 {
        color: #1e293b !important;
        font-weight: 700 !important;
        letter-spacing: -0.3px;
    }
    
    /* 버튼 - 모던 그라데이션 */
    .stButton > button {
        border-radius: 12px;
        border: none;
        background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);
        color: white;
        font-weight: 600;
        padding: 0.5rem 1.2rem;
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(79, 70, 229, 0.25);
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(79, 70, 229, 0.35);
        background: linear-gradient(135deg, #4338ca 0%, #4f46e5 100%);
    }
    
    /* 다운로드 버튼 - 초록 계열 */
    .stDownloadButton > button {
        border-radius: 12px;
        border: none;
        background: linear-gradient(135deg, #059669 0%, #10b981 100%);
        color: white;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(5, 150, 105, 0.25);
        transition: all 0.2s ease;
    }
    .stDownloadButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(5, 150, 105, 0.35);
    }
    
    /* 컨테이너 카드 느낌 */
    [data-testid="stExpander"] {
        border-radius: 14px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        background: white;
    }
    
    /* 입력 필드 */
    .stTextInput > div > div > input,
    .stTextArea textarea,
    .stNumberInput > div > div > input {
        border-radius: 10px;
        border: 1px solid #cbd5e1;
    }
    
    /* metric 카드 */
    [data-testid="stMetric"] {
        background: white;
        border-radius: 14px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        border: 1px solid #e2e8f0;
    }
    
    /* 사이드바 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #334155 100%);
    }
    [data-testid="stSidebar"] * {
        color: #f1f5f9 !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        background: rgba(255,255,255,0.1);
        box-shadow: none;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255,255,255,0.2);
    }
    
    /* 구분선 */
    hr {
        border-color: #e2e8f0;
    }
    
    /* 알림 박스 둥글게 */
    .stAlert {
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 세션 상태 초기화
# ==========================================
if "projects" not in st.session_state:
    st.session_state.projects = []

if "current_project" not in st.session_state:
    st.session_state.current_project = None

if "claude_client" not in st.session_state:
    st.session_state.claude_client = None

# ==========================================
# 유틸리티 함수들
# ==========================================

def initialize_claude():
    """Claude API 초기화"""
    api_key = st.secrets.get("CLAUDE_API_KEY")
    if api_key:
        return Anthropic(api_key=api_key)
    return None

def analyze_style(text):
    """기존 세특에서 문체 분석"""
    client = initialize_claude()
    if not client:
        st.error("Claude API 키가 설정되지 않았습니다.")
        return None
    
    prompt = f"""다음 세특들을 분석해서 작성자의 문체 특징을 요약해줘.

세특 텍스트:
{text}

분석 항목:
1. 어조 & 성향 (긍정적/구체적/성장중심 등)
2. 자주 사용하는 표현 (상위 5개)
3. 문장 구조 패턴
4. 평균 문장 길이
5. 강조 포인트

JSON 형식으로 정리해줘:
{{
  "tone": ["...", "..."],
  "frequent_expressions": ["...", "..."],
  "sentence_pattern": "...",
  "avg_length": "...",
  "emphasis": ["...", "..."]
}}"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # JSON 파싱 시도
        response_text = message.content[0].text
        # JSON 부분 추출
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
        except:
            return {"raw": response_text}
        
        return {"raw": response_text}
    except Exception as e:
        st.error(f"분석 중 오류: {e}")
        return None

def extract_pdf_text(uploaded_file):
    """업로드된 PDF에서 텍스트 추출"""
    try:
        import pypdf
        reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        st.error(f"PDF 읽기 오류: {e}")
        return ""


def analyze_plan_for_units(plan_text):
    """평가계획서 텍스트에서 단원·활동 목록을 AI로 추출"""
    client = initialize_claude()
    if not client:
        st.error("Claude API 키가 설정되지 않았습니다.")
        return None
    
    prompt = f"""다음은 학교 평가계획서야. 여기서 세특을 작성할 만한 단원과 활동을 뽑아줘.

평가계획서 내용:
{plan_text[:6000]}

각 단원을 아래 형식의 JSON 배열로만 출력해줘. 다른 설명은 절대 붙이지 마.
[
  {{"단원": "소인수분해", "활동": "퍼즐 활동", "평가방법": "수행평가"}},
  {{"단원": "정수와 유리수", "활동": "", "평가방법": "지필평가"}}
]"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        import json
        text = message.content[0].text
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
        return None
    except Exception as e:
        st.error(f"분석 오류: {e}")
        return None


def build_apps_script(results, project):
    """구글시트에 세특을 반별 시트로 자동 입력하는 Apps Script 코드 생성"""
    import json
    
    # 반별로 데이터 묶기
    classes = {}
    for r in results:
        cls = str(r.get('class', '') or '미분류').strip()
        if cls not in classes:
            classes[cls] = []
        classes[cls].append({
            "이름": r['student'],
            "수준": r['level'],
            "세특": r['seteuk'],
            "바이트": len(r['seteuk'].encode('utf-8'))
        })
    
    # 각 반 안에서 번호 매기기
    classes_data = {}
    for cls, students in classes.items():
        numbered = []
        for idx, s in enumerate(students):
            numbered.append({"번호": idx + 1, **s})
        classes_data[cls] = numbered
    
    data_json = json.dumps(classes_data, ensure_ascii=False, indent=2)
    
    subject = project.get('subject', '교과')
    unit = project.get('unit_name', '')
    title = f"{subject}"
    if unit:
        title = f"{subject} - {unit}"
    
    code = f'''/**
 * 교과 세특 자동 입력 스크립트
 * {title}
 *
 * [사용법]
 * 1. 구글 스프레드시트에서 확장 프로그램 > Apps Script 열기
 * 2. 이 코드를 전부 붙여넣고 저장(디스크 아이콘 또는 Ctrl+S)
 * 3. 상단 함수 선택칸에 insertSeteuk 확인 후 실행(▶) 클릭
 * 4. 권한 요청이 뜨면 본인 계정으로 허용
 * 5. 반별로 시트가 생성되며 세특이 자동 입력됩니다
 */

function insertSeteuk() {{
  var classesData = {data_json};

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var headers = ["번호", "이름", "수준", "세특", "바이트"];
  var totalCount = 0;

  // 반별로 시트 생성
  for (var className in classesData) {{
    var data = classesData[className];

    var sheet = ss.getSheetByName(className);
    if (!sheet) {{
      sheet = ss.insertSheet(className);
    }}
    sheet.clear();

    // 헤더
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight("bold").setBackground("#e8eaed");

    // 데이터
    var rows = [];
    for (var i = 0; i < data.length; i++) {{
      rows.push([data[i]["번호"], data[i]["이름"], data[i]["수준"], data[i]["세특"], data[i]["바이트"]]);
    }}
    if (rows.length > 0) {{
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
      sheet.getRange(2, 4, rows.length, 1).setWrap(true);
    }}

    // 보기 좋게 정리
    sheet.setColumnWidth(1, 50);
    sheet.setColumnWidth(2, 90);
    sheet.setColumnWidth(3, 60);
    sheet.setColumnWidth(4, 600);
    sheet.setColumnWidth(5, 70);
    sheet.setFrozenRows(1);

    totalCount += data.length;
  }}

  SpreadsheetApp.getUi().alert("반별 시트에 세특 " + totalCount + "건이 입력되었습니다!");
}}
'''
    return code


def calculate_similarity(text1, text2):
    """개선된 유사도 계산 (단어 + 글자 TF-IDF 조합)"""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        
        # 단어 단위 유사도 (표현 겹침을 잘 잡음)
        try:
            vw = TfidfVectorizer(analyzer='word', ngram_range=(1, 2))
            vecs_w = vw.fit_transform([text1, text2])
            sim_w = cosine_similarity(vecs_w[0:1], vecs_w[1:2])[0][0]
        except:
            sim_w = 0
        
        # 글자 단위 유사도 (어미 변화까지 잡음)
        vc = TfidfVectorizer(analyzer='char', ngram_range=(2, 3))
        vecs_c = vc.fit_transform([text1, text2])
        sim_c = cosine_similarity(vecs_c[0:1], vecs_c[1:2])[0][0]
        
        # 단어 60% + 글자 40% 가중 평균
        similarity = (sim_w * 0.6 + sim_c * 0.4) * 100
        return round(similarity, 1)
    except:
        # sklearn이 없으면 간단한 방식으로 폴백
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if len(words1 | words2) == 0:
            return 0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        similarity = (intersection / union) * 100
        
        return round(similarity, 1)

def check_forbidden_words(text, forbidden_words):
    """금지어 검사"""
    found = []
    for word in forbidden_words:
        if word in text:
            found.append(word)
    return found

def generate_seteuk(project, style_profile=None, school_rules=None, student_info=None):
    """세특 생성"""
    client = initialize_claude()
    if not client:
        st.error("Claude API 키가 설정되지 않았습니다.")
        return None
    
    # 프롬프트 구성
    prompt_parts = [
        "너는 한국 중학교의 우수한 세특 작성자야.",
        "",
        "## 지침",
        "1. 구체적이고 긍정적인 표현 사용",
        "2. 학생의 노력과 성장 강조",
        "3. 부정적 표현 절대 금지",
        "4. 다양한 표현으로 학생별 차별화",
        "5. ★문장 끝맺음(어미)을 다양하게 할 것. '~보임', '~함', '~임' 같은 같은 어미를 연달아 반복하지 말고 문장마다 다르게 끝맺을 것. 특히 '~보임'의 남발 금지.",
        "6. 학생을 지칭할 때 '급우', '친구들' 같은 표현은 쓰지 말 것. 필요하면 '학급 구성원', '모둠원' 등으로 표현.",
    ]
    
    # 내 작성 방식 추가 (예시 기반 - 가장 강력)
    my_examples = project.get('my_examples', '').strip()
    my_rules = project.get('my_rules', '').strip()
    
    if my_examples:
        prompt_parts.extend([
            "",
            "## ★★ 따라야 할 작성 스타일 (이 선생님이 직접 쓴 실제 세특 예시)",
            "아래는 이 선생님이 직접 작성한 세특이야. 이 말투, 문장 구조, 끝맺음, 서술 순서를 그대로 모방해서 써줘.",
            "내용은 학생에 맞게 새로 쓰되, '쓰는 방식'은 아래 예시와 똑같이 느껴지도록 할 것.",
            "",
            my_examples,
        ])
    
    if my_rules:
        prompt_parts.extend([
            "",
            "## ★ 이 선생님의 작성 규칙 (반드시 지킬 것)",
            my_rules,
        ])
    
    # 학교 규정 추가
    if school_rules:
        prompt_parts.extend([
            "",
            "## 학교 규정",
            f"필수 문체: {school_rules.get('required_style', '자유')}",
            f"금지어: {', '.join(school_rules.get('forbidden_words', []))}",
        ])
    
    # 평가계획서 참고자료 추가
    plan_text = project.get('plan_text', '').strip()
    if plan_text:
        prompt_parts.extend([
            "",
            "## 참고자료 (학교 평가계획서 발췌)",
            "아래는 이 학교의 평가계획서야. 단원의 성격과 평가 맥락을 참고해서 세특을 작성해줘.",
            plan_text[:3000],
        ])
    
    # 강조 영역 추가
    if school_rules and school_rules.get('emphasis'):
        prompt_parts.extend([
            f"강조할 영역: {', '.join(school_rules.get('emphasis', []))} (이 부분이 드러나도록 서술)",
        ])
    
    # 단원 정보 추가
    unit_name = project.get('unit_name', '')
    activity_name = project.get('activity_name', '')
    achievement_std = project.get('achievement_std', '')
    if unit_name or activity_name or achievement_std:
        prompt_parts.extend([
            "",
            "## 단원 및 활동 정보",
        ])
        if unit_name:
            prompt_parts.append(f"단원: {unit_name}")
        if activity_name:
            prompt_parts.append(f"활동: {activity_name}")
        if achievement_std:
            prompt_parts.append(f"성취기준: {achievement_std} (이 성취기준에 맞는 내용으로 작성)")
    
    # 학생 정보 추가
    if student_info:
        level = student_info.get('level', '')
        
        # 학생 수준에 맞는 표현 풀 찾기 (activity_desc는 "A (매우우수)" 형태의 키)
        expression_pool = ''
        for key, val in project.get('activity_desc', {}).items():
            if key.strip().upper().startswith(str(level).strip().upper()) and val.strip():
                expression_pool = val.strip()
                break
        
        prompt_parts.extend([
            "",
            "## 이 학생 정보",
            f"이름: {student_info.get('name', '')}",
            f"성취수준: {level}",
            f"주요특성: {student_info.get('main_trait', '')}",
            f"부수특성: {student_info.get('sub_traits', '')}",
        ])
        
        if expression_pool:
            prompt_parts.extend([
                "",
                "## ★★★ 이 수준 학생에게 쓸 표현들 (가장 중요 - 최대한 살릴 것)",
                "아래는 선생님이 이 수준 학생에게 직접 쓰려고 준비한 표현들이야. 한 줄에 하나씩 있어.",
                "이 중에서 1~2개를 골라, 그 표현의 어휘와 말투를 최대한 그대로 살려서 세특을 작성해줘.",
                "표현을 통째로 새로 지어내지 말고, 아래 표현을 뼈대로 삼아 학생의 특성만 자연스럽게 덧붙이는 방식으로 쓸 것.",
                "단, 학생마다 다른 표현을 고르거나 다르게 조합해서 서로 똑같아지지 않게 할 것.",
                "",
                expression_pool,
            ])
        
        # 수준별 차등 서술 지침
        prompt_parts.extend([
            "",
            "## 성취수준별 서술 강도 (반드시 반영)",
            "- A(매우우수): 자기주도성, 깊은 이해, 탁월한 적용까지 강조",
            "- B(우수): 정확한 이해와 능숙한 적용을 강조",
            "- C(보통): 성실한 참여와 기본 개념 이해를 강조",
            "- D(기초): 꾸준한 노력과 성장 가능성을 강조",
            "- E(불충분): 참여 태도와 작은 진전, 긍정적 변화를 강조",
            f"→ 이 학생은 {level}수준이므로 그에 맞는 강도로 서술할 것. 수준에 맞지 않게 과장하지 말 것.",
        ])
    
    target = project.get('unit_target_bytes') or project.get('target_bytes', 450)
    # 한글 기준 대략 글자 수 (1글자 ≈ 2바이트)
    approx_chars = int(target / 2)
    # 안전 목표: 초과를 막기 위해 목표보다 약간 적게 쓰도록 유도
    safe_chars = int(target * 0.9 / 2)
    prompt_parts.extend([
        "",
        "## 작성 요청",
        "위 조건을 반영해서 세특 1개를 생성해줘.",
        "",
        "## 분량 (★★ 가장 중요한 규칙 - 반드시 지킬 것)",
        f"- 절대 상한선: {target}바이트. 이걸 넘으면 완전히 실패한 결과임.",
        f"- 바이트 계산법: 한글 1글자=2바이트, 영문/숫자/공백/문장부호=1바이트.",
        f"- 목표 분량: 한글 약 {safe_chars}자 (넉넉잡아 최대 {approx_chars}자). 상한선보다 살짝 적게 쓸 것.",
        f"- 쓰고 나서 길이를 스스로 점검하고, {target}바이트에 가깝거나 넘으면 문장을 덜어내서 줄일 것.",
        "- 문장 수를 3~4문장 이내로 제한하면 분량을 맞추기 쉬움.",
        "- 세특 본문만 출력. 글자수/바이트수 표기나 부연 설명은 절대 붙이지 말 것.",
        "",
        "구체적이고 다양하게 작성하되, 위 분량 규칙을 최우선으로 지켜줘.",
    ])
    
    prompt = "\n".join(prompt_parts)
    
    import time
    last_error = None
    for attempt in range(3):  # 최대 3번 시도
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text.strip()
        except Exception as e:
            last_error = e
            if attempt < 2:
                time.sleep(2)  # 2초 쉬고 다시 시도
    
    # 3번 다 실패
    st.warning(f"⚠️ 생성 실패 (3회 시도): {last_error}")
    return None

# ==========================================
# 메인 UI
# ==========================================

st.title("🎓 교과 세특 생성 플랫폼 v2.0")

st.markdown("""
**새로운 버전의 특징:**
- 📚 **문체 학습**: 기존 세특에서 스타일 학습
- 🎯 **학생별 차별화**: 특성 태그로 맞춤형 생성
- ⚠️ **품질 검사**: 중복도 & 규정 자동 검증
- 📋 **학교 규정 적용**: 금지어, 필수문체 관리
""")

st.divider()

# ==========================================
# 좌측 메뉴
# ==========================================

with st.sidebar:
    st.markdown("### 📍 메뉴")
    
    menu = st.radio(
        "선택",
        ["🏠 메인", "➕ 새 프로젝트", "📂 프로젝트 열기", "⚙️ 설정"],
        label_visibility="collapsed"
    )
    
    st.divider()
    
    st.markdown("### 📋 프로젝트")
    if st.session_state.projects:
        for i, proj in enumerate(st.session_state.projects):
            with st.container(border=True):
                st.write(f"**{proj.get('subject', '')}** {proj.get('grade', '')} {proj.get('classes', '')}")
                st.caption(f"생성일: {proj.get('created_date', '')}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📖 열기", key=f"open_{i}"):
                        st.session_state.current_project = i
                        st.rerun()
                with col2:
                    if st.button("🗑️ 삭제", key=f"delete_{i}"):
                        st.session_state.projects.pop(i)
                        st.rerun()
    else:
        st.info("프로젝트가 없습니다")

# ==========================================
# 페이지별 콘텐츠
# ==========================================

if menu == "🏠 메인":
    st.markdown("## 최근 프로젝트")
    
    if st.session_state.projects:
        for i, proj in enumerate(st.session_state.projects):
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("교과", proj.get('subject', '-'))
                with col2:
                    st.metric("학년", proj.get('grade', '-'))
                with col3:
                    st.metric("반", proj.get('classes', '-'))
                with col4:
                    st.metric("진행도", f"{proj.get('step', 1)}/6")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("📖 열기", key=f"main_open_{i}"):
                        st.session_state.current_project = i
                        st.rerun()
                with col_btn2:
                    if st.button("🗑️ 삭제", key=f"main_delete_{i}"):
                        st.session_state.projects.pop(i)
                        st.rerun()
    else:
        st.info("📭 새 프로젝트를 만들어보세요!")

elif menu == "➕ 새 프로젝트":
    st.markdown("## 새 프로젝트 생성")
    
    with st.form("new_project_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            subject = st.selectbox("교과", ["수학", "국어", "영어", "사회", "과학", "기술가정", "체육", "음악", "미술", "기타(직접입력)"])
            subject_custom = st.text_input("교과명 직접입력 ('기타' 선택 시)", placeholder="예: 정보, 한문, 도덕")
            grade = st.radio("학년", [1, 2, 3], horizontal=True)
        
        with col2:
            num_classes = st.number_input("반 수", min_value=1, max_value=11, value=5, step=1,
                help="입력칸의 +/- 버튼을 쓰거나, 숫자를 전부 지운 뒤 새로 입력하세요")
            students_per_class = st.number_input("반당 학생 수", min_value=1, max_value=50, value=30, step=1,
                help="입력칸의 +/- 버튼을 쓰거나, 숫자를 전부 지운 뒤 새로 입력하세요")
        
        st.divider()
        
        col3, col4 = st.columns(2)
        with col3:
            target_bytes = st.number_input("목표 바이트", min_value=100, max_value=1000, value=450)
        with col4:
            final_goal = st.number_input("1학기 최종 목표", min_value=100, max_value=2000, value=900)
        
        st.divider()
        
        st.markdown("### 성취수준 선택")
        num_levels = st.radio("성취수준 개수", [3, 5], horizontal=True)
        
        submitted = st.form_submit_button("✅ 프로젝트 생성", use_container_width=True)
        
        if submitted:
            # 기타 선택 시 직접입력값 사용
            final_subject = subject
            if subject == "기타(직접입력)":
                final_subject = subject_custom.strip() if subject_custom.strip() else "기타"
            
            new_project = {
                "subject": final_subject,
                "grade": f"{grade}학년",
                "classes": f"{num_classes}반",
                "students_per_class": students_per_class,
                "target_bytes": target_bytes,
                "final_goal": final_goal,
                "num_levels": num_levels,
                "created_date": datetime.now().strftime("%Y-%m-%d"),
                "step": 1,
                "style_profile": None,
                "school_rules": None,
                "students": []
            }
            st.session_state.projects.append(new_project)
            st.session_state.current_project = len(st.session_state.projects) - 1
            st.success("✅ 프로젝트가 생성되었습니다!")
            st.rerun()

elif menu == "⚙️ 설정":
    st.markdown("## 설정")
    
    st.markdown("### 🔑 Claude API 키 설정")
    st.info("""
    **로컬에서 실행할 때:**
    1. `.streamlit/secrets.toml` 파일 생성
    2. 다음 내용 추가:
    ```
    CLAUDE_API_KEY = "sk-..."
    ```
    
    **Streamlit Cloud에 배포할 때:**
    1. 프로젝트 설정 → Secrets
    2. 위와 동일하게 입력
    """)
    
    # API 키 테스트
    if st.button("🔗 API 키 테스트"):
        client = initialize_claude()
        if client:
            try:
                test_msg = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "OK"}]
                )
                st.success("✅ API 키가 정상입니다!")
            except Exception as e:
                st.error(f"❌ 오류: {e}")
        else:
            st.error("❌ API 키가 설정되지 않았습니다.")

# ==========================================
# 프로젝트 진행 화면
# ==========================================

if st.session_state.current_project is not None:
    # 유효한 프로젝트 번호인지 확인 (삭제 등으로 범위를 벗어나면 초기화)
    if (not st.session_state.projects or 
            st.session_state.current_project < 0 or 
            st.session_state.current_project >= len(st.session_state.projects)):
        st.session_state.current_project = None
    else:
        st.divider()
        
        proj = st.session_state.projects[st.session_state.current_project]
    
        st.markdown(f"## 📝 {proj['subject']} {proj['grade']} {proj['classes']}")
    
        # 진행도 표시
        progress_steps = ["기본정보", "문체학습", "규정설정", "학생정보", "단원정보", "세특생성"]
        current_step = proj.get('step', 1)
    
        progress_cols = st.columns(len(progress_steps))
        for i, step_name in enumerate(progress_steps):
            with progress_cols[i]:
                if i < current_step:
                    st.markdown(f"✅ {step_name}")
                elif i == current_step - 1:
                    st.markdown(f"▶️ **{step_name}**")
                else:
                    st.markdown(f"⭕ {step_name}")
    
        st.divider()
    
        # Step 1: 기본정보 (이미 완료)
        if current_step == 1:
            st.markdown("## ✅ 1단계: 기본 정보 (완료)")
        
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("교과", proj['subject'])
                col2.metric("학년", proj['grade'])
                col3.metric("반", proj['classes'])
                # 실제 등록된 학생이 있으면 그 수를, 없으면 반수×반당인원으로 계산
                if proj.get('students'):
                    student_count = len(proj['students'])
                else:
                    try:
                        cls_num = int(''.join(filter(str.isdigit, str(proj.get('classes', '0')))))
                        student_count = proj.get('students_per_class', 0) * cls_num
                    except:
                        student_count = 0
                col4.metric("학생수", student_count)
        
            if st.button("➡️ 다음 단계로"):
                proj['step'] = 2
                st.rerun()
    
        # Step 2: 문체 학습
        elif current_step == 2:
            st.markdown("## 📚 2단계: 내 작성 방식 등록")
            st.caption("선생님만의 세특 작성 방식을 알려주면, AI가 그 방식을 따라 씁니다. (선택사항이지만 강력 추천)")
        
            st.markdown("### ✍️ 1) 내 세특 예시")
            st.info("예전에 직접 쓰신 세특 2~3개를 붙여넣으세요. AI가 이 말투와 구조를 그대로 따라 씁니다. (가장 효과 큼)")
        
            my_examples = st.text_area(
                "내 세특 예시 (여러 개면 줄바꿈으로 구분)",
                value=proj.get('my_examples', ''),
                height=180,
                placeholder="예시)\n소인수분해 단원에서 합성수를 소수의 곱으로 표현하는 원리를 정확히 이해하고, 이를 다양한 문제에 능숙하게 적용함. 풀이 과정을 논리적으로 설명하는 태도가 돋보임.\n\n정수와 유리수의 사칙연산에서 음수 개념을 명확히 파악하고, 연산 규칙을 정확하게 적용하여 복잡한 계산도 끝까지 정확히 해결함."
            )
        
            st.markdown("### 📋 2) 내 작성 규칙")
            st.info("본인만의 원칙이 있으면 자유롭게 적으세요. 없으면 비워둬도 됩니다.")
        
            my_rules = st.text_area(
                "내 작성 규칙 (자유롭게)",
                value=proj.get('my_rules', ''),
                height=120,
                placeholder="예시)\n- 문장은 '~함' 체로 끝낸다\n- 학업 역량을 먼저 쓰고 태도를 뒤에 쓴다\n- 구체적인 활동 사례를 반드시 하나 포함한다\n- 한 가지 활동을 깊게 서술한다"
            )
        
            proj['my_examples'] = my_examples
            proj['my_rules'] = my_rules
        
            if my_examples.strip() or my_rules.strip():
                st.success("✅ 작성 방식이 등록되었습니다. 이 방식대로 세특이 생성됩니다.")
        
            if st.button("➡️ 다음 단계로"):
                proj['step'] = 3
                st.rerun()
    
        # Step 3: 규정 설정
        elif current_step == 3:
            st.markdown("## 📋 3단계: 학교 규정 설정")
        
            with st.expander("필수 문체", expanded=True):
                required_style = st.selectbox(
                    "필수 문체 선택",
                    ["자유", "함 체", "보임 체"],
                    help="학교의 공식 문체"
                )
        
            with st.expander("금지어 설정", expanded=True):
                forbidden_words = st.multiselect(
                    "금지어 선택",
                    ["선행학습", "천재적", "타고난", "의대 수준", "대학 과정", 
                     "미흡", "태만", "산만", "도움이 필요", "부족", "급우", "친구들"],
                    default=["선행학습", "천재적", "타고난", "의대 수준", "대학 과정", "급우"]
                )
            
                custom_word = st.text_input("커스텀 금지어 추가 (예: ~해야한다)")
                if custom_word and st.button("추가"):
                    forbidden_words.append(custom_word)
        
            with st.expander("강조 영역 (선택)", expanded=False):
                emphasis = st.multiselect(
                    "강조할 영역",
                    ["인성", "창의성", "협업", "도전정신", "학습습관"]
                )
        
            school_rules = {
                "required_style": required_style,
                "forbidden_words": forbidden_words,
                "emphasis": emphasis
            }
        
            proj['school_rules'] = school_rules
        
            if st.button("➡️ 다음 단계로"):
                proj['step'] = 4
                st.rerun()
    
        # Step 4: 학생 정보
        elif current_step == 4:
            st.markdown("## 👥 4단계: 학생 정보 입력")
        
            st.markdown("### CSV 파일 업로드")
            st.info("형식: 번호, 이름, 반, 수준, 주요특성, 부수특성")
        
            uploaded_file = st.file_uploader("CSV 파일 선택", type=["csv"])
        
            if uploaded_file is not None:
                try:
                    df = pd.read_csv(uploaded_file, encoding='utf-8')
                except:
                    df = pd.read_csv(uploaded_file, encoding='cp949')
            
                st.markdown("### 📊 업로드된 데이터")
                st.dataframe(df, use_container_width=True)
            
                # 컬럼명 자동 감지 (영문/한글 모두 지원)
                col_mapping = {}
                for col in df.columns:
                    col_lower = col.lower().strip()
                    if '번호' in col or 'number' in col_lower:
                        col_mapping['number'] = col
                    elif '이름' in col or 'name' in col_lower:
                        col_mapping['name'] = col
                    elif '반' in col or 'class' in col_lower:
                        col_mapping['class'] = col
                    elif '수준' in col or 'level' in col_lower:
                        col_mapping['level'] = col
                    elif '특성' in col or 'trait' in col_lower:
                        if '주요' in col or 'main' in col_lower:
                            col_mapping['main_trait'] = col
                        elif '부수' in col or 'sub' in col_lower:
                            col_mapping['sub_traits'] = col
            
                # 학생 정보 저장
                students = []
                for idx, row in df.iterrows():
                    students.append({
                        "number": row.get(col_mapping.get('number', '번호'), idx + 1),
                        "name": row.get(col_mapping.get('name', '이름'), ''),
                        "class": row.get(col_mapping.get('class', '반'), ''),
                        "level": row.get(col_mapping.get('level', '수준'), 'A'),
                        "main_trait": row.get(col_mapping.get('main_trait', '주요특성'), ''),
                        "sub_traits": row.get(col_mapping.get('sub_traits', '부수특성'), '')
                    })
            
                proj['students'] = students
                st.success(f"✅ {len(students)}명 학생 정보 저장됨")
            
                if st.button("➡️ 다음 단계로"):
                    proj['step'] = 5
                    st.rerun()
    
        # Step 5: 단원 정보
        elif current_step == 5:
            st.markdown("## 📚 5단계: 단원 정보")
            
            # 평가계획서 업로드 (선택)
            with st.expander("📎 참고자료 올리기 — 평가계획서·교육과정·세특작성지침 등 (선택)", expanded=False):
                st.info("평가계획서, 교육과정 문서, 세특 작성지침 등을 올리면 AI가 참고해서 세특을 씁니다. 평가계획서의 경우 단원 목록도 자동으로 뽑아줍니다.\n\n📌 **한글 파일은 PDF로 저장해서 올려주세요.** (한글에서 다른 이름으로 저장 → PDF 선택)")
                st.warning("⚠️ **비용 절약 안내:** 자료가 길수록 생성 비용이 올라갑니다. 교육과정 총론처럼 수백 페이지짜리 전체를 올리기보다, **필요한 부분(해당 단원, 핵심 지침)만 발췌해서** 올리는 것을 권장합니다. 너무 긴 자료는 앞부분 일부만 반영됩니다.")
                
                plan_file = st.file_uploader("참고자료 PDF 업로드", type=["pdf"], key="plan_pdf")
                
                if plan_file is not None:
                    if st.button("🔍 자료 분석하기"):
                        with st.spinner("자료를 읽고 단원을 추출하는 중..."):
                            plan_text = extract_pdf_text(plan_file)
                            if plan_text:
                                # 비용 보호: 참고자료는 최대 3000자까지만 사용
                                MAX_CHARS = 3000
                                original_len = len(plan_text)
                                if original_len > MAX_CHARS:
                                    plan_text = plan_text[:MAX_CHARS]
                                    st.warning(f"📏 자료가 {original_len:,}자로 깁니다. 비용 절약을 위해 **앞부분 {MAX_CHARS:,}자만** 참고자료로 사용합니다. 특정 단원만 반영하려면 그 부분만 발췌해서 다시 올려주세요.")
                                else:
                                    st.success(f"✅ 자료 {original_len:,}자를 모두 참고자료로 사용합니다.")
                                
                                proj['plan_text'] = plan_text  # 참고자료로도 저장
                                units = analyze_plan_for_units(plan_text)
                                if units:
                                    proj['extracted_units'] = units
                                    st.rerun()
                
                # 추출된 단원 목록 표시
                if proj.get('extracted_units'):
                    st.markdown("**📋 추출된 단원 (단원명 칸에 넣을 것을 고르세요):**")
                    for u in proj['extracted_units']:
                        unit_label = f"{u.get('단원','')}"
                        if u.get('활동'):
                            unit_label += f" / {u.get('활동')}"
                        if u.get('평가방법'):
                            unit_label += f" ({u.get('평가방법')})"
                        col_u1, col_u2 = st.columns([4, 1])
                        with col_u1:
                            st.write(f"• {unit_label}")
                        with col_u2:
                            if st.button("선택", key=f"pick_unit_{u.get('단원','')}"):
                                proj['unit_name'] = u.get('단원', '')
                                proj['activity_name'] = u.get('활동', '')
                                st.rerun()
                    st.caption("💡 평가계획서 내용은 세특 생성 시 참고자료로도 활용됩니다.")
            
            col1, col2 = st.columns(2)
            with col1:
                unit_name = st.text_input("단원명", value=proj.get('unit_name', ''))
            with col2:
                activity_name = st.text_input("활동명", value=proj.get('activity_name', ''))
        
            achievement_std = st.text_input("성취기준 (선택)", value=proj.get('achievement_std', ''))
        
            st.markdown("### 📏 이 단원의 세특 분량")
            unit_target_bytes = st.number_input(
                "목표 바이트 (한글 1글자 = 2바이트)",
                min_value=100, max_value=1500,
                value=proj.get('unit_target_bytes') or proj.get('target_bytes', 450),
                step=10,
                help="예: 450바이트 ≈ 한글 약 225자. 단원마다 다르게 지정할 수 있습니다."
            )
            st.caption(f"💡 약 한글 {int(unit_target_bytes/2)}자 분량으로 생성됩니다")
        
            st.markdown("### 📝 성취수준별 표현 풀(pool)")
            st.info("각 수준마다 평소 쓰시는 표현을 **여러 개(5개 정도) 줄바꿈으로** 입력하세요. AI가 이 표현들을 최대한 살려서 학생별 세특을 작성합니다.")
            levels = ["A (매우우수)", "B (우수)", "C (보통)", "D (기초)", "E (불충분)"][:proj.get('num_levels', 5)]
            
            placeholders = {
                "A (매우우수)": "소인수분해 퍼즐 문제를 매우 우수하게 해결하였음\n복잡한 합성수도 막힘 없이 소인수분해함\n원리를 정확히 이해하고 다양한 문제에 능숙하게 적용함",
                "C (보통)": "소인수분해 퍼즐 문제를 무난하게 해결함\n기본 원리를 이해하고 주어진 문제에 적용함\n활동에 성실히 참여하며 풀이 과정을 따라감",
                "E (불충분)": "소인수분해 퍼즐 활동에 참여함\n기초 개념을 익히기 위해 꾸준히 노력함",
            }
            
            activity_descriptions = {}
            for level in levels:
                activity_descriptions[level] = st.text_area(
                    f"{level} 표현들 (한 줄에 하나씩)",
                    value=proj.get('activity_desc', {}).get(level, ''),
                    height=120,
                    placeholder=placeholders.get(level, "이 수준 학생에게 쓰는 표현을 한 줄에 하나씩 입력")
                )
            
            proj['unit_name'] = unit_name
            proj['activity_name'] = activity_name
            proj['achievement_std'] = achievement_std
            proj['activity_desc'] = activity_descriptions
            proj['unit_target_bytes'] = unit_target_bytes
        
            if st.button("➡️ 세특 생성 준비"):
                proj['step'] = 6
                st.rerun()
    
        # Step 6: 세특 생성 & 품질 검사
        elif current_step == 6:
            st.markdown("## 🚀 6단계: 세특 생성")
        
            with st.container(border=True):
                st.markdown("### 📊 생성 준비")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("학생 수", len(proj.get('students', [])))
                col2.metric("작성방식", "등록됨" if (proj.get('my_examples','').strip() or proj.get('my_rules','').strip()) else "기본")
                col3.metric("규정", "설정됨" if proj.get('school_rules') else "미설정")
                col4.metric("목표", f"{proj.get('unit_target_bytes') or proj.get('target_bytes')}B")
        
            if st.button("🎯 세특 생성 시작", use_container_width=True):
                st.markdown("### ⏳ 생성 중...")
                progress_bar = st.progress(0)
                status_text = st.empty()
            
                results = []
                total_students = len(proj.get('students', []))
            
                for i, student in enumerate(proj.get('students', [])):
                    status_text.text(f"생성 중: {student['name']} ({i+1}/{total_students})")
                
                    # 세특 생성
                    seteuk = generate_seteuk(
                        proj,
                        school_rules=proj.get('school_rules'),
                        student_info=student
                    )
                
                    if seteuk:
                        results.append({
                            "student": student['name'],
                            "class": student.get('class', ''),
                            "level": student['level'],
                            "seteuk": seteuk,
                            "bytes": len(seteuk.encode('utf-8'))
                        })
                
                    progress = (i + 1) / total_students
                    progress_bar.progress(progress)
            
                status_text.text("✅ 생성 완료!")
            
                # 품질 검사
                st.markdown("### 📊 품질 검사 중...")
            
                # 중복도 검사
                duplicates = []
                for i, result1 in enumerate(results):
                    for j, result2 in enumerate(results):
                        if i < j:
                            similarity = calculate_similarity(result1['seteuk'], result2['seteuk'])
                            if similarity > 65:
                                duplicates.append({
                                    "student1": result1['student'],
                                    "student2": result2['student'],
                                    "similarity": round(similarity, 1)
                                })
            
                # 금지어 검사
                forbidden_warnings = []
                forbidden_words = proj.get('school_rules', {}).get('forbidden_words', [])
                for result in results:
                    found = check_forbidden_words(result['seteuk'], forbidden_words)
                    if found:
                        forbidden_warnings.append({
                            "student": result['student'],
                            "words": found
                        })
            
                # 결과 저장
                proj['results'] = results
                proj['quality_check'] = {
                    "duplicates": duplicates,
                    "forbidden_warnings": forbidden_warnings
                }
            
                # 결과 표시
                st.markdown("---")
            
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("생성된 세특", len(results))
                with col2:
                    st.metric("중복 경고", len(duplicates))
                with col3:
                    st.metric("금지어 검출", len(forbidden_warnings))
            
                if len(duplicates) > 0:
                    st.markdown("### ⚠️ 중복도 높은 쌍")
                    for dup in duplicates:
                        st.warning(f"{dup['student1']} vs {dup['student2']}: {dup['similarity']}% 유사도")
            
                if len(forbidden_warnings) > 0:
                    st.markdown("### ⚠️ 금지어 검출")
                    for warning in forbidden_warnings:
                        st.warning(f"{warning['student']}: {', '.join(warning['words'])} 포함")
            
                st.success(f"✅ 총 {len(results)}명의 세특이 생성되었습니다!")
        
            # 생성된 결과가 있으면 항상 표시 (수정/재생성/다운로드 포함)
            if proj.get('results'):
                results = proj['results']
                
                st.divider()
                st.markdown("### ✏️ 생성된 세특 (수정 · 재생성 가능)")
                st.caption("세특을 직접 고치거나, 학생별로 다시 생성할 수 있습니다. 고친 내용은 바로 저장됩니다.")
                
                import pandas as pd
                
                for idx, r in enumerate(results):
                    byte_len = len(r['seteuk'].encode('utf-8'))
                    target = proj.get('unit_target_bytes') or proj.get('target_bytes', 450)
                    over = byte_len > target
                    label = f"{idx+1}. {r['student']} ({r['level']}) — {byte_len}B"
                    if over:
                        label += " ⚠️초과"
                    
                    with st.expander(label, expanded=False):
                        # 수정 가능한 텍스트 영역
                        edited = st.text_area(
                            "세특 내용",
                            value=r['seteuk'],
                            height=140,
                            key=f"edit_{idx}"
                        )
                        # 수정 내용이 바뀌면 저장
                        if edited != r['seteuk']:
                            results[idx]['seteuk'] = edited
                            results[idx]['bytes'] = len(edited.encode('utf-8'))
                            proj['results'] = results
                        
                        cur_bytes = len(edited.encode('utf-8'))
                        st.caption(f"현재 {cur_bytes}바이트 / 목표 {target}바이트")
                        
                        # 이 학생만 재생성
                        if st.button(f"🔄 {r['student']} 세특 다시 생성", key=f"regen_{idx}"):
                            # 해당 학생 정보 찾기
                            student = None
                            for s in proj.get('students', []):
                                if s['name'] == r['student']:
                                    student = s
                                    break
                            if student:
                                with st.spinner(f"{r['student']} 세특 재생성 중..."):
                                    new_seteuk = generate_seteuk(
                                        proj,
                                        school_rules=proj.get('school_rules'),
                                        student_info=student
                                    )
                                if new_seteuk:
                                    results[idx]['seteuk'] = new_seteuk
                                    results[idx]['bytes'] = len(new_seteuk.encode('utf-8'))
                                    proj['results'] = results
                                    st.rerun()
                
                # 다운로드용 표
                st.divider()
                st.markdown("### 📥 결과 다운로드")
                
                download_df = pd.DataFrame([
                    {
                        "번호": idx + 1,
                        "이름": r['student'],
                        "수준": r['level'],
                        "세특": r['seteuk'],
                        "바이트": len(r['seteuk'].encode('utf-8'))
                    }
                    for idx, r in enumerate(results)
                ])
                
                col_dl1, col_dl2, col_dl3 = st.columns(3)
                
                # 엑셀 다운로드
                with col_dl1:
                    try:
                        import io
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            download_df.to_excel(writer, index=False, sheet_name='세특')
                        buffer.seek(0)
                        file_name = f"세특_{proj.get('subject','')}_{proj.get('unit_name','')}.xlsx"
                        st.download_button(
                            label="📊 엑셀(.xlsx)",
                            data=buffer,
                            file_name=file_name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"엑셀 생성 오류: {e}")
                
                # CSV 다운로드
                with col_dl2:
                    csv_data = download_df.to_csv(index=False).encode('utf-8-sig')
                    csv_name = f"세특_{proj.get('subject','')}_{proj.get('unit_name','')}.csv"
                    st.download_button(
                        label="📄 CSV",
                        data=csv_data,
                        file_name=csv_name,
                        mime="text/csv",
                        use_container_width=True
                    )
                
                # 구글시트 Apps Script 코드 다운로드
                with col_dl3:
                    script_code = build_apps_script(results, proj)
                    st.download_button(
                        label="📋 구글시트 코드",
                        data=script_code.encode('utf-8'),
                        file_name=f"세특_구글시트_{proj.get('subject','')}.gs",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                st.markdown("### 📋 생성된 세특 전체 보기")
                st.dataframe(download_df, use_container_width=True, height=400)
                
                with st.expander("📖 구글시트 코드 사용법"):
                    st.markdown("""
                    1. 위 **📋 구글시트 코드** 버튼을 눌러 `.gs` 파일을 받으세요.
                    2. 구글 스프레드시트를 새로 만들고, 메뉴에서 **확장 프로그램 → Apps Script**를 엽니다.
                    3. 기존 내용을 지우고, 받은 파일 내용을 붙여넣은 뒤 저장합니다.
                    4. 상단의 **실행(▶)** 버튼을 누르면, 세특이 시트에 자동으로 입력됩니다.
                    5. 권한 요청이 뜨면 본인 계정으로 허용해 주세요.
                    """)

st.divider()

st.markdown("""
---
**💡 팁:** 
- 문체 학습을 활용하면 일관된 문체의 세특이 생성됩니다
- 학교 규정을 설정하면 감사 때 문제가 될 표현을 자동으로 검출합니다
- 학생의 주요특성을 입력하면 학생별 차별화된 세특이 생성됩니다
""")
