import os
import requests
import pandas as pd
from bs4 import BeautifulSoup

# FDA 510(k) search result page (same as you see in the browser)
BASE_URL = "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm"

# Decision Date range
START_DATE = "11/16/2025"
END_DATE   = "11/22/2025"

def fetch_510k_decision_range(start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch 510(k) devices for a decision date range from pmn.cfm result page.
    Uses GET with query parameters to mimic the browser search.
    """
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
    )

    # 쿼리 파라미터 (브라우저에서 검색할 때와 최대한 유사하게)
    params = {
        "start_search": "1",
        "DecisionDateFrom": start_date,
        "DecisionDateTo": end_date,
        "sortcolumn": "DecisionDate",
        "sortdirection": "DESC",
        "PageSize": "500",        # 한 페이지 최대 500건
    }

    print(f"[INFO] Requesting FDA 510(k) list {start_date} ~ {end_date}")
    res = session.get(BASE_URL, params=params, timeout=60)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")

    # 결과 테이블 찾기
    # pmn.cfm 구조에서 결과 테이블은 일반적으로 첫 번째 <table> 또는
    # 특정 summary/title을 가진 테이블일 수 있음
    tables = soup.find_all("table")
    if not tables:
        print("[WARN] No <table> elements found in HTML.")
        return pd.DataFrame()

    # 첫 번째 테이블이 헤더/메뉴일 수 있어서, 열 수가 많은 테이블을 선택
    candidate = None
    max_cols = 0
    for t in tables:
        dfs = pd.read_html(str(t))
        if not dfs:
            continue
        df_tmp = dfs[0]
        if df_tmp.shape[1] > max_cols and "Device Name" in df_tmp.columns:
            candidate = df_tmp
            max_cols = df_tmp.shape[1]

    if candidate is None:
        # fallback: 그냥 첫 번째 테이블
        candidate = pd.read_html(str(tables[0]))[0]
        print("[WARN] Used first table as fallback (no 'Device Name' header match).")

    print(f"[INFO] Retrieved {len(candidate)} rows from FDA page.")
    return candidate


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    df = fetch_510k_decision_range(START_DATE, END_DATE)

    if df is None or df.empty:
        print("[ERROR] No data rows found, saving empty file for debug.")
        df = pd.DataFrame()

    out_path = "data/raw_data.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[INFO] saved {len(df)} rows to {out_path}")
