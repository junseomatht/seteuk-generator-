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
    
    # 문체 프로필 추가
    if style_profile:
        prompt_parts.extend([
            "",
            "## 문체 프로필",
            f"어조: {', '.join(style_profile.get('tone', []))}",
            f"자주 쓰는 표현: {', '.join(style_profile.get('frequent_expressions', []))}",
            f"패턴: {style_profile.get('sentence_pattern', '')}",
        ])
    
    # 학교 규정 추가
    if school_rules:
        prompt_parts.extend([
            "",
            "## 학교 규정",
            f"필수 문체: {school_rules.get('required_style', '자유')}",
            f"금지어: {', '.join(school_rules.get('forbidden_words', []))}",
        ])
    
    # 학생 정보 추가
    if student_info:
        prompt_parts.extend([
            "",
            "## 학생 정보",
            f"이름: {student_info.get('name', '')}",
            f"수준: {student_info.get('level', '')}",
            f"주요특성: {student_info.get('main_trait', '')}",
            f"부수특성: {student_info.get('sub_traits', '')}",
            f"활동: {student_info.get('activity', '')}",
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
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
    except Exception as e:
        st.error(f"생성 중 오류: {e}")
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
            subject = st.selectbox("교과", ["수학", "국어", "영어", "사회", "과학", "기술가정", "체육", "음악", "미술"])
            grade = st.radio("학년", [1, 2, 3], horizontal=True)
        
        with col2:
            num_classes = st.number_input("반 수", min_value=1, max_value=11, value=5)
            students_per_class = st.number_input("반당 학생 수", min_value=1, max_value=50, value=30)
        
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
            new_project = {
                "subject": subject,
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
            col4.metric("학생수", proj['students_per_class'] * proj['classes'].rstrip('반'))
        
        if st.button("➡️ 다음 단계로"):
            proj['step'] = 2
            st.rerun()
    
    # Step 2: 문체 학습
    elif current_step == 2:
        st.markdown("## 📚 2단계: 문체 학습")
        
        style_mode = st.radio(
            "문체 모드 선택",
            ["🔷 기본 모드", "🟦 학교 표준형", "🟦 내 문체 학습 (권장!)"],
            help="내 문체 학습: 작년 세특 10개 이상 업로드하면 더 좋은 결과!"
        )
        
        if "내 문체 학습" in style_mode:
            st.markdown("### 기존 세특 업로드")
            st.info("같은 교과의 기존 세특 10개 이상을 업로드하세요")
            
            uploaded_file = st.file_uploader("파일 선택 또는 드래그", type=["csv", "txt"])
            
            if uploaded_file is not None:
                st.markdown("### 📊 분석 중...")
                progress_bar = st.progress(0)
                
                # 파일 읽기
                content = uploaded_file.read().decode('utf-8')
                
                # Claude 분석
                with st.spinner("문체 분석 중..."):
                    style_result = analyze_style(content)
                
                progress_bar.progress(100)
                
                if style_result:
                    st.markdown("### ✅ 분석 완료!")
                    
                    st.json(style_result)
                    
                    proj['style_profile'] = style_result
                    
                    if st.button("✨ 이 문체로 적용"):
                        proj['step'] = 3
                        st.rerun()
        else:
            st.info("기본 문체를 사용합니다")
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
        
        st.markdown("### 성취수준별 활동 설명")
        levels = ["A (매우우수)", "B (우수)", "C (보통)", "D (기초)", "E (불충분)"][:proj.get('num_levels', 5)]
        
        activity_descriptions = {}
        for level in levels:
            activity_descriptions[level] = st.text_area(
                f"{level} 활동설명",
                value=proj.get('activity_desc', {}).get(level, ''),
                height=60
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
            col2.metric("문체", "학습됨" if proj.get('style_profile') else "기본")
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
                    style_profile=proj.get('style_profile'),
                    school_rules=proj.get('school_rules'),
                    student_info=student
                )
                
                if seteuk:
                    results.append({
                        "student": student['name'],
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
        
        # 생성된 결과가 있으면 항상 표시 (다운로드 포함)
        if proj.get('results'):
            results = proj['results']
            
            st.divider()
            st.markdown("### 📥 결과 다운로드")
            
            # 표 형태로 정리
            import pandas as pd
            download_df = pd.DataFrame([
                {
                    "번호": idx + 1,
                    "이름": r['student'],
                    "수준": r['level'],
                    "세특": r['seteuk'],
                    "바이트": r['bytes']
                }
                for idx, r in enumerate(results)
            ])
            
            col_dl1, col_dl2 = st.columns(2)
            
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
                        label="📊 엑셀(.xlsx)로 다운로드",
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
                    label="📄 CSV로 다운로드",
                    data=csv_data,
                    file_name=csv_name,
                    mime="text/csv",
                    use_container_width=True
                )
            
            st.markdown("### 📋 생성된 세특 전체 보기")
            st.dataframe(download_df, use_container_width=True, height=400)

st.divider()

st.markdown("""
---
**💡 팁:** 
- 문체 학습을 활용하면 일관된 문체의 세특이 생성됩니다
- 학교 규정을 설정하면 감사 때 문제가 될 표현을 자동으로 검출합니다
- 학생의 주요특성을 입력하면 학생별 차별화된 세특이 생성됩니다
""")
