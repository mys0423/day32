# 텍스트 분석 기록 앱 UI: 입력 > 처리 > 저장 > 이력 > 통계

import uuid  # 유일한 식별값 생성 라이브러리
import psycopg
import streamlit as st
from day32_logic import analysis_text
from day32_db import save_run, list_runs, get_run, summary, delete_run
from util.print_util import pp


# 결과 표시 함수
def show_result(result):
    left, right = st.columns(2)
    left.metric('공백 제외 글자 수', result['char_count'])
    right.metric('공백 기준 단어 수', result['word_count'])
    st.write('상위 토큰 : ', result['top_tokens'])


def main():
    st.set_page_config(page_title='텍스트 분석 기록', layout='wide')
    st.title('텍스트 분석과 클라우드 기록')

    # session_state에 request_key가 없다면
    if 'request_key' not in st.session_state:
        # uuid 라이브러리를 활용해서 uuid 생성해 저장
        st.session_state['request_key'] = str(uuid.uuid4())
    if 'result' not in st.session_state:  # 결과
        st.session_state['result'] = None
    if 'saved' not in st.session_state:  # 저장 여부
        st.session_state['saved'] = False

    analysis, history = st.tabs(['분석과 저장', '이력과 통계'])

    with analysis:
        with st.form('analysis'):
            text = st.text_area('분석할 문장', max_chars=5000)
            submitted = st.form_submit_button('분석 실행')

        if submitted:
            try:
                result = analysis_text(text)
                st.session_state['result'] = result
                st.session_state['request_key'] = str(uuid.uuid4())
                st.session_state['saved'] = False
            except ValueError as e:
                st.warning(str(e))

        # [수정 1] 이 아래부터 들여쓰기를 if submitted 블록 밖으로 뺐습니다!
        result = st.session_state['result']
        if result is not None:
            st.text(result['text'])
            show_result(result)

            # 오타 수정 (기록 제외 -> 기록 제목)
            title = st.text_input('기록 제목', max_chars=80)

            if st.button('결과 저장', disabled=st.session_state['saved']):
                try:
                    rid = save_run(
                        title, result, st.session_state['request_key']
                    )
                    st.session_state['saved'] = True
                    st.success('이미 저장한 결과입니다.' if rid is None else f'기록 {rid} 저장 완료')
                    pp('분석 저장 완료')
                except ValueError as ve:
                    st.warning(str(ve))
                except psycopg.Error as pe:
                    pp(f'저장 오류: {type(pe).__name__}')
                    st.error('저장 실패. 연결/권한/테이블을 확인하고 재시도하세요.')
                except OSError as ose:
                    st.error('sql폴더를 확인하세요.')

    with history:
        try:
            stats = summary()
            a, b, c = st.columns(3)
            a.metric('전체 저장 건수', stats['total'])

            # 오타 수정 (누적 금지 수 -> 누적 글자 수)[cite: 26]
            b.metric('누적 글자 수', stats['total_chars'])
            c.metric('평균 단어 수', str(stats['average_words']))

            keyword = st.text_input('기록 제목 검색', max_chars=80)

            st.button('이력 새로고침')

            rows = list_runs(keyword)
            st.caption('목록은 최신 100건, 위 통계는 전체 저장 데이터 기준입니다.')
            st.dataframe(rows, hide_index=True, use_container_width=True)

            if rows:
                rid = st.selectbox('전체 기록 ID', [x['id'] for x in rows])
                record = get_run(rid)

                if record:
                    st.subheader(record['title'])
                    st.text(record['source_text'])
                    show_result(record)
                    st.caption(f"처리 버전: {record['analysis_version']}")

                    # [수정 2] 에러 발생 원인이던 selectbox를 checkbox로 변경[cite: 27]
                    confirm = st.checkbox('선택한 기록 삭제 확인')

                    if st.button('기록 삭제', disabled=not confirm):
                        if delete_run(rid):
                            st.rerun()
                        else:
                            st.warning('이미 삭제된 기록입니다.')
                else:
                    st.info('기록이 사라졌습니다. 새로고침하세요.')
            else:
                st.info('저장된 기록 또는 검색 결과가 없습니다.')

        except ValueError as ve:
            st.warning(str(ve))
        except psycopg.Error as pe:
            pp(f'조회 오류: {type(pe).__name__}')
            st.error('이력 조회 실패. DB연결과 text_runs 테이블을 확인하세요.')
        except OSError as ose:
            st.error('sql폴더를 확인하세요.')


if __name__ == '__main__':
    main()