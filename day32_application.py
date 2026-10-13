# import os
# import uuid
# import psycopg
# from psycopg.rows import dict_row
# import streamlit as st
# from dotenv import load_dotenv
#
# # 로컬 환경변수 로드
# load_dotenv()
#
#
# # ==========================================
# # 1. Logic 계층 (순수 계산 함수)
# # ==========================================
# def calculate_balance(income: int, expense: int) -> dict:
#     """수입과 지출을 받아 예상 잔액을 계산합니다."""
#     if income < 0 or income > 100000000:
#         raise ValueError("수입은 0~100,000,000 사이로 입력하세요.")
#     if expense < 0 or expense > 100000000:
#         raise ValueError("지출은 0~100,000,000 사이로 입력하세요.")
#
#     return {
#         'income': income,
#         'expense': expense,
#         'balance': income - expense
#     }
#
#
# # ==========================================
# # 2. DB 계층 (SQL 직접 포함)
# # ==========================================
# def get_db_url():
#     url = os.getenv('DATABASE_URL', '').strip()
#     if not url:
#         raise ValueError("DATABASE_URL 환경변수를 설정하세요.")
#     return url
#
#
# def save_plan(title: str, result: dict, request_key: str):
#     title = title.strip()
#     if not title or len(title) > 80:
#         raise ValueError("계획 제목은 1~80자 이내로 입력하세요.")
#
#     sql = """
#         INSERT INTO budget_plans (title, income, expense, balance, request_key)
#         VALUES (%s, %s, %s, %s, %s)
#         ON CONFLICT (request_key) DO NOTHING
#         RETURNING id;
#     """
#     with psycopg.connect(get_db_url(), row_factory=dict_row) as conn:
#         row = conn.execute(sql, (
#             title, result['income'], result['expense'], result['balance'], request_key
#         )).fetchone()
#         return row['id'] if row else None
#
#
# def list_plans(keyword=''):
#     sql = """
#         SELECT id, title, income, expense, balance
#         FROM budget_plans
#         WHERE title ILIKE %s
#         ORDER BY id DESC
#         LIMIT 100;
#     """
#     with psycopg.connect(get_db_url(), row_factory=dict_row) as conn:
#         return conn.execute(sql, (f'%{keyword.strip()}%',)).fetchall()
#
#
# def get_plan(plan_id: int):
#     sql = """
#         SELECT id, title, income, expense, balance
#         FROM budget_plans
#         WHERE id = %s;
#     """
#     with psycopg.connect(get_db_url(), row_factory=dict_row) as conn:
#         row = conn.execute(sql, (plan_id,)).fetchone()
#         return row if row else None
#
#
# def summary_plans():
#     sql = """
#         SELECT count(*) AS total_count,
#                COALESCE(sum(balance), 0) AS total_balance
#         FROM budget_plans;
#     """
#     with psycopg.connect(get_db_url(), row_factory=dict_row) as conn:
#         return conn.execute(sql).fetchone()
#
#
# # ==========================================
# # 3. UI 계층 (Streamlit)
# # ==========================================
# def main():
#     st.set_page_config(page_title="예산 계획 앱", layout="wide")
#     st.title("💸 예산 계획 및 저장")
#
#     if 'request_key' not in st.session_state:
#         st.session_state['request_key'] = str(uuid.uuid4())
#     if 'result' not in st.session_state:
#         st.session_state['result'] = None
#     if 'saved' not in st.session_state:
#         st.session_state['saved'] = False
#
#     tab_calc, tab_hist = st.tabs(['계산과 저장', '이력과 통계'])
#
#     with tab_calc:
#         with st.form("calc_form"):
#             income = st.number_input("수입 (원)", min_value=0, max_value=100000000, step=1000)
#             expense = st.number_input("지출 (원)", min_value=0, max_value=100000000, step=1000)
#             calc_btn = st.form_submit_button("계산 미리보기")
#
#         if calc_btn:
#             try:
#                 res = calculate_balance(income, expense)
#                 st.session_state['result'] = res
#                 st.session_state['request_key'] = str(uuid.uuid4())
#                 st.session_state['saved'] = False
#             except ValueError as e:
#                 st.warning(str(e))
#
#         res = st.session_state['result']
#         if res is not None:
#             col1, col2, col3 = st.columns(3)
#             col1.metric("수입", f"{res['income']:,} 원")
#             col2.metric("지출", f"{res['expense']:,} 원")
#             col3.metric("예상 잔액", f"{res['balance']:,} 원")
#
#             title = st.text_input("계획 제목 (1~80자)", max_chars=80)
#
#             if st.button("결과 저장", disabled=st.session_state['saved']):
#                 try:
#                     pid = save_plan(title, res, st.session_state['request_key'])
#                     st.session_state['saved'] = True
#
#                     if pid is None:
#                         st.success("이미 저장한 결과입니다.")
#                     else:
#                         st.success(f"✅ 기록 {pid} 저장 완료!")
#                 except ValueError as ve:
#                     st.warning(str(ve))
#                 except psycopg.Error:
#                     st.error("DB 연결 또는 저장에 실패했습니다. 연결 상태를 확인하세요.")
#
#     with tab_hist:
#         try:
#             stats = summary_plans()
#             sc1, sc2 = st.columns(2)
#             sc1.metric("전체 계획 건수", stats['total_count'])
#             sc2.metric("전체 잔액 합계", f"{stats['total_balance']:,} 원")
#
#             keyword = st.text_input("계획 제목 검색", max_chars=80)
#             st.button("이력 새로고침")
#
#             rows = list_plans(keyword)
#             st.caption("목록은 최신 100건, 위 통계는 전체 데이터 기준입니다.")
#             st.dataframe(rows, hide_index=True, use_container_width=True)
#
#             if rows:
#                 pid = st.selectbox("상세 조회할 기록 ID", [x['id'] for x in rows])
#                 detail = get_plan(pid)
#
#                 if detail:
#                     st.subheader(f"📄 {detail['title']}")
#                     dc1, dc2, dc3 = st.columns(3)
#                     dc1.metric("상세 수입", f"{detail['income']:,} 원")
#                     dc2.metric("상세 지출", f"{detail['expense']:,} 원")
#                     dc3.metric("상세 잔액", f"{detail['balance']:,} 원")
#                 else:
#                     st.info("상세 정보를 불러올 수 없습니다.")
#             else:
#                 st.info("저장된 계획이 없습니다.")
#
#         except psycopg.Error:
#             st.error("이력 조회 실패. DB연결과 budget_plans 테이블을 확인하세요.")
#
#
# if __name__ == "__main__":
#     main()

# day32_application.py

import os
import uuid
import psycopg
from psycopg.rows import dict_row
import streamlit as st
from util.print_util import pp, up
from dotenv import load_dotenv

load_dotenv()

def db(sql, params=()):
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise ValueError("DATABASE_URL 환경변수를 설정하세요.")
    with psycopg.connect(
        url, connect_timeout=15, row_factory=dict_row,
        prepare_threshold=None,
    ) as conn:
        return conn.execute(sql, params).fetchall()  # 값 바인딩, 결과 목록

def main():
    st.title("월간 예산 계획")
    if "budget_preview" not in st.session_state:
        st.session_state["budget_preview"] = None
    try:
        with st.form("budget"):
            title = st.text_input("계획 제목", max_chars=80)
            income = st.number_input("수입(원)", 0, 100000000, step=1000)
            expense = st.number_input("지출(원)", 0, 100000000, step=1000)
            ok = st.form_submit_button("계산 미리보기")
        if ok:
            if not title.strip():
                st.warning("계획 제목을 입력하세요.")
            else:
                st.session_state["budget_preview"] = {
                    "title": title.strip(), "income": int(income),
                    "expense": int(expense), "balance": int(income - expense),
                    "key": str(uuid.uuid4()),
                }  # 새 계산 결과마다 새로운 요청 키
        p = st.session_state["budget_preview"]
        if p:
            st.write(p["title"])
            st.metric("예상 잔액", f"{p['balance']:,}원")
            if st.button("계획 저장"):
                rows = db(
                    "INSERT INTO budget_plans "
                    "(title, income, expense, balance, request_key) "
                    "VALUES (%s, %s, %s, %s, %s) "
                    "ON CONFLICT (request_key) DO NOTHING RETURNING id",
                    (p["title"], p["income"], p["expense"],
                     p["balance"], p["key"]),
                )
                st.success("저장 완료" if rows else "이미 저장한 계획입니다.")
        stats = db(
            "SELECT count(*) AS total, "
            "COALESCE(sum(balance), 0) AS balance_sum FROM budget_plans"
        )[0]
        st.write("전체 계획:", stats["total"], "잔액 합계:", stats["balance_sum"])
        keyword = st.text_input("제목 검색", max_chars=80)
        rows = db(
            "SELECT id, title, balance FROM budget_plans "
            "WHERE title ILIKE %s ORDER BY id DESC LIMIT 100",
            (f"%{keyword.strip()}%",),
        )
        st.dataframe(rows, hide_index=True, use_container_width=True)
        if rows:
            rid = st.selectbox("상세 ID", [x["id"] for x in rows])
            detail = db("SELECT * FROM budget_plans WHERE id = %s", (rid,))
            if detail:
                st.write({k: detail[0][k] for k in
                          ("title", "income", "expense", "balance")})
            else:
                st.info("기록이 사라졌습니다.")
    except ValueError as exc:
        st.warning(str(exc))
    except psycopg.Error as exc:
        pp("DB 오류 유형:", type(exc).__name__)
        st.error("연결·권한·budget_plans 테이블을 확인하세요.")

if __name__ == "__main__":
    main()
