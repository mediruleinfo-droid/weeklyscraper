import os
import io
import requests
import pandas as pd
from bs4 import BeautifulSoup

# 검색 페이지
SEARCH_URL = "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfPMN/pmn.cfm"

# 날짜 범위 (MM/DD/YYYY 형식)
START_DATE = "11/16/2025"
END_DATE   = "11/22/2025"


def get_search_result_html(start_date: str, end_date: str) -> str:
    """
    Decision Date 범위로 검색한 결과 HTML(목록 화면)을 가져온다.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    # 검색 조건: Decision Date, 정렬은 Decision Date descending, page size 500
data = {
    "KNumber": "",
    "Panel": "",
    "ProductCode": "",
    "Applicant": "",
    "DeviceName": "",
    "DecisionDateFrom": start_date,  # "11/16/2025"
    "DecisionDateTo": end_date,      # "11/22/2025"
    "sortcolumn": "DecisionDate",
    "sortdirection": "DESC",
    "Pagesize": "500",
    "StartRec": "1",
    "Search": "Search",
}

    print(f"[INFO] Requesting search HTML {start_date} ~ {end_date}")
    res = session.post(SEARCH_URL, data=data, timeout=60)
    res.raise_for_status()
    return res.text, session

def get_export_csv(session: requests.Session, html: str) -> pd.DataFrame:
    """
    검색 결과 화면의 HTML에서 Export to Excel 폼(action, hidden 필드)을 읽어
    같은 값으로 POST하여 CSV를 받아온다.
    """
    soup = BeautifulSoup(html, "html.parser")

    # pmn.cfm 페이지에 있는 main form (id나 name이 pmnform 인 경우가 많음)
    form = soup.find("form", {"id": "pmnform"}) or soup.find("form", {"name": "pmnform"})
    if form is None:
        raise RuntimeError("Cannot find pmnform on the page.")

    # form action (상대경로일 수 있음)
    action = form.get("action")
    if not action:
        raise RuntimeError("Form has no action attribute.")

    if action.startswith("http"):
        export_url = action
    else:
        # 상대경로이면 같은 도메인 기준으로 합치기
        from urllib.parse import urljoin
        export_url = urljoin(SEARCH_URL, action)

    # hidden input 등 모든 form 필드 읽기
    payload = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        value = inp.get("value", "")
        payload[name] = value

    # Results per Page 500 보장 (필드 이름은 페이지 HTML에 맞춰 조정 필요)
    payload["Pagesize"] = payload.get("Pagesize", "500")

    print(f"[INFO] Posting to export URL: {export_url}")
    res = session.post(export_url, data=payload, timeout=60)
    res.raise_for_status()

    # 응답이 CSV 또는 XLS 형태. 첨부하신 파일은 CSV이므로 CSV로 가정.
    content_type = res.headers.get("Content-Type", "").lower()
    text = res.text

    # pandas로 CSV 파싱
    df = pd.read_csv(io.StringIO(text))
    print(f"[INFO] Export CSV rows: {len(df)}")
    return df


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)

    html, session = get_search_result_html(START_DATE, END_DATE)
    df = get_export_csv(session, html)

    out_path = "data/raw_data.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[INFO] saved {len(df)} rows to {out_path}")
