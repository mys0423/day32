# import os
# import math
# import psycopg
# from psycopg.rows import dict_row
# import streamlit as st
# from dotenv import load_dotenv
#
# # 로컬 환경변수 로드
# load_dotenv()
#
# # ==========================================
# # 1. Logic 계층 (UI와 DB를 참조하지 않는 순수 함수)
# # ==========================================
# def calculate_shipping_fee(weight: int) -> int:
#     """무게(g)를 입력받아 배송비를 계산하여 반환합니다."""
#     if weight < 1 or weight > 20000:
#         raise ValueError("무게는 1g에서 20000g 사이로 입력해 주세요.")
#
#     if weight <= 1000:
#         return 3000
#     else:
#         # 1000g 초과 시, 시작된 1000g 구간마다 1000원 추가 (올림 처리)
#         extra_weight = weight - 1000
#         extra_fee = math.ceil(extra_weight / 1000) * 1000
#         return 3000 + extra_fee
#
#
# # ==========================================
# # 2. DB 계층
# # ==========================================
# def get_db_url():
#     url = os.getenv('DATABASE_URL', '').strip()
#     if not url:
#         raise ValueError("DATABASE_URL 환경변수를 설정하세요.")
#     return url
#
#
# def save_quote(label: str, weight: int, fee: int, rule_version: str):
#     label = label.strip()
#     if not label:
#         raise ValueError("견적 제목을 입력해 주세요. (공백 불가)")
#     if len(label) > 80:
#         raise ValueError("견적 제목은 80자 이내로 입력해 주세요.")
#
#     sql = """
#         INSERT INTO shipping_quotes (label, weight, fee, rule_version)
#         VALUES (%s, %s, %s, %s)
#         RETURNING id;
#     """
#     with psycopg.connect(get_db_url(), row_factory=dict_row) as conn:
#         result = conn.execute(sql, (label, weight, fee, rule_version)).fetchone()
#         return result['id']
#
#
# def list_quotes(limit=100):
#     sql = """
#         SELECT id, label, weight, fee, rule_version
#         FROM shipping_quotes
#         ORDER BY id DESC
#         LIMIT %s;
#     """
#     with psycopg.connect(get_db_url(), row_factory=dict_row) as conn:
#         return conn.execute(sql, (limit,)).fetchall()
#
#
# # ==========================================
# # 3. UI 계층 (Streamlit)
# # ==========================================
# def main():
#     st.set_page_config(page_title="배송비 견적 계산기", layout="centered")
#     st.title("📦 배송비 견적 계산 및 저장")
#     st.caption("1000g 이하 3000원 / 초과 시 1000g 구간마다 1000원 추가")
#
#     # [입력 및 실행 폼]
#     with st.form("quote_form"):
#         label = st.text_input("견적 제목 (1~80자)", max_chars=80, placeholder="예: 서울 강남구 발송건")
#         weight = st.number_input("무게 (g)", min_value=1, max_value=20000, value=1000, step=1)
#         submitted = st.form_submit_button("계산하고 저장")
#
#     if submitted:
#         try:
#             # 1. 로직 함수 호출 (계산)
#             fee = calculate_shipping_fee(weight)
#
#             # 2. DB 저장 함수 호출
#             rule_version = "shipping-v1"
#             inserted_id = save_quote(label, weight, fee, rule_version)
#
#             # 3. 결과 표시
#             st.success(f"✅ 저장 성공! (기록 ID: {inserted_id})")
#             st.info(f"💰 계산된 요금: {fee:,}원 (입력 무게: {weight}g)")
#
#         except ValueError as ve:
#             st.warning(str(ve))
#         except psycopg.Error as pe:
#             st.error("DB 연결 또는 저장에 실패했습니다. 서버 상태나 권한을 확인하세요.")
#             st.write(pe)
#
#     st.divider()
#
#     # [이력 목록 조회]
#     st.subheader("최신 견적 목록 (최대 100건)")
#     try:
#         rows = list_quotes(100)
#         if rows:
#             st.dataframe(rows, hide_index=True, use_container_width=True)
#         else:
#             st.info("아직 저장된 견적이 없습니다.")
#     except psycopg.Error:
#         st.error("목록을 불러오는 데 실패했습니다. DB 연결이나 테이블 존재 여부를 확인하세요.")
#     except ValueError as ve:
#         st.warning(str(ve))
#
#
# if __name__ == "__main__":
#     main()


import os
import psycopg
from psycopg.rows import dict_row
import streamlit as st
from dotenv import load_dotenv
from util.print_util import pp

load_dotenv()

# DB 연결하고 쿼리 실행하는 함수
def db(sql, params=()):
    url = os.getenv("DATABASE_URL", '').strip()
    if not url:
        raise ValueError("DATABASE_URL 환경변수를 설정하세요.")
    with psycopg.connect(
        url,
        connect_timeout=15,
        row_factory=dict_row
    ) as conn:
        return conn.execute(sql, params).fetchall()

# 중량에 따라 배송비 리턴하는 함수
def shipping_fee(weight):
    return 3000 if weight <= 1000 else 3000 + ((weight-1) // 1000) * 1000

def main():
    st.title('배송비 견적 기록')
    try:
        with st.form('quote'):
            label = st.text_input('견적 제목', max_chars=80)
            weight = st.number_input('무게(g)', 1, 20000, 1000, step=1)
            ok = st.form_submit_button('계산하고 저장')
        if ok:
            if not label.strip():
                st.warning('제목을 입력하세요.')
            else:
                fee = shipping_fee(int(weight)) # 배송비 계산
                rows = db(
                    ' INSERT INTO SHIPPING_QUOTES '
                    ' (LABEL, WEIGHT, FEE, RULE_VERSION) '
                    ' VALUES (%s, %s, %s, %s) RETURNING ID ',
                    (label.strip(), int(weight), fee, 'shipping-v1')
                )
                st.success(f"{fee:,}원, 기록 {rows[0]['id']} 저장")

            # 목록 조회 후 데이터프레임에 표시
            rows = db(' SELECT * FROM SHIPPING_QUOTES ORDER BY ID DESC LIMIT 100 ')
            st.dataframe(rows, hide_index=True, use_container_width=True)

    except ValueError as ve:
        st.warning(str(ve))
    except psycopg.Error as pe:
        pp('DB오류 - 유형: ', type(pe).__name__)
        st.error('연결/권한/테이블을 확인하세요.')

if __name__ == '__main__':
    main()