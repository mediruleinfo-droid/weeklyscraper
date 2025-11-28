import os
import io
import requests
import pandas as pd
from bs4 import BeautifulSoup

SEARCH_URL = "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfPMN/pmn.cfm"

START_DATE = "11/16/2025"
END_DATE   = "11/22/2025"


def get_search_result_html(start_date: str, end_date: str) -> str:
    """Decision Date 범위로 검색한 결과 HTML(목록 화면)을 가져온다."""
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
    """검색 결과 화면에서 Export to Excel CSV를 받아온다."""
    soup = BeautifulSoup(html, "html.parser")

    form = soup.find("form", {"id": "pmnform"}) or soup.find("form", {"name": "pmnform"})
    if form is None:
        raise RuntimeError("Cannot find pmnform on the page.")

    action = form.get("action")
    if not action:
        raise RuntimeError("Form has no action attribute.")

    from urllib.parse import urljoin
    export_url = action if action.startswith("http") else urljoin(SEARCH_URL, action)

    payload = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        value = inp.get("value", "")
        payload[name] = value

    payload["Pagesize"] = payload.get("Pagesize", "500")

    print(f"[INFO] Posting to export URL: {export_url}")
    res = session.post(export_url, data=payload, timeout=60)
    res.raise_for_status()

    df = pd.read_csv(io.StringIO(res.text))
    print(f"[INFO] Export CSV rows: {len(df)}")
    return df


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)

    html, session = get_search_result_html(START_DATE, END_DATE)
    df = get_export_csv(session, html)

    out_path = "data/raw_data.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[INFO] saved {len(df)} rows to {out_path}")
