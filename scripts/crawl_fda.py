import os
import io
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, urljoin

import requests
import pandas as pd
from bs4 import BeautifulSoup


SEARCH_URL = "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfPMN/pmn.cfm"

# 크롤링할 기간 (MM/DD/YYYY)
START_DATE = "11/16/2025"
END_DATE = "11/22/2025"


def search_by_decision_date(start_date: str, end_date: str):
    """
    BasicSearch 폼에 DecisionDateFrom/To 를 넣고 Search를 눌렀을 때와 동일한 결과 페이지를 가져온다.
    반환값: (html, session, final_url)
    """
    session = requests.Session()
    session.headers.update(
        {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )

    # 날짜 검색 폼 구조에 맞춘 payload
    data = {
        "KNumber": "",
        "ProductCode": "",
        "Center": "",
        "CombinationProducts": "",
        "Applicant": "",
        "DeviceName": "",
        "Panel": "",
        "ThirdPartyReviewed": "",
        "Decision": "",
        "ClinicalTrials": "",
        "IVDProducts": "",
        "redact510K": "",
        "PCCP": "",
        "DecisionDateFrom": start_date,  # 예: "11/16/2025"
        "DecisionDateTo": end_date,      # 예: "11/22/2025"
        "SortColumn": "dd_desc",         # Decision Date (descending)
        "Search": "Search",              # 검색 버튼
    }

    print(f"[INFO] Requesting search HTML {start_date} ~ {end_date}")
    res = session.post(SEARCH_URL, data=data, timeout=60)
    res.raise_for_status()
    return res.text, session, res.url


def build_rpp500_url(url: str) -> str:
    """
    검색 결과 URL 의 쿼리스트링을 분석해서,
    한 페이지에 최대 500개가 보이도록 PAGENUM 등을 조정한 URL을 만든다.
    (DecisionDateFrom/To 등 기존 조건은 유지)
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    # 검색 결과 URL이 쿼리스트링 없이 돌아온 경우를 대비한 예외 처리
    # 이 경우에는 현재 START_DATE/END_DATE 를 기반으로 새 쿼리를 구성한다.
    if not qs:
        qs = {
            "start_search": ["1"],
            "Center": [""],
            "Panel": [""],
            "ProductCode": [""],
            "KNumber": [""],
            "Applicant": [""],
            "DeviceName": [""],
            "Type": [""],
            "ThirdPartyReviewed": [""],
            "ClinicalTrials": [""],
            "Decision": [""],
            "DecisionDateFrom": [START_DATE],
            "DecisionDateTo": [END_DATE],
            "IVDProducts": [""],
            "Redact510K": [""],
            "CombinationProducts": [""],
            "PCCP": [""],
            "ZNumber": [""],
            "PAGENUM": ["500"],
            "SortColumn": [""],
        }
    else:
        # 기존 쿼리에서 페이지 크기/시작 위치만 조정
        qs["PAGENUM"] = ["500"]
        qs["start_search"] = ["1"]

    new_query = urlencode(qs, doseq=True)
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)


def get_rpp500_page(session: requests.Session, url: str):
    """
    PAGENUM=500 이 반영된 URL로 GET 요청을 보내
    한 페이지에 모든 결과가 보이는 HTML을 가져온다.
    """
    rpp_url = build_rpp500_url(url)
    print(f"[INFO] Requesting rpp=500 page: {rpp_url}")
    res = session.get(rpp_url, timeout=60)
    res.raise_for_status()
    return res.text, res.url


def download_export_csv(session: requests.Session, html: str, base_url: str) -> pd.DataFrame:
    """
    rpp=500 결과 페이지 HTML에서
    form name='subpmnform' (id='pmnform') 을 찾아
    그 action(pmnExcel.cfm) 으로 POST 하여 CSV를 받아온다.
    """
    soup = BeautifulSoup(html, "html.parser")

    # subpmnform / id=pmnform 폼 찾기
    form = (
        soup.find("form", {"name": "subpmnform"})
        or soup.find("form", {"id": "pmnform"})
    )
    if form is None:
        raise RuntimeError("Cannot find subpmnform/pnmform on the page.")

    action = form.get("action")
    if not action:
        raise RuntimeError("Export form has no action attribute.")

    export_url = urljoin(base_url, action)

    # hidden input 등 모든 필드 수집 (특히 ID=K250927,... 리스트)
    payload = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        if not name:
            continue
        value = inp.get("value", "")
        payload[name] = value

    print(f"[INFO] Posting to export form: {export_url}")
    res = session.post(export_url, data=payload, timeout=60)
    res.raise_for_status()

    # 응답은 CSV 텍스트 (PMNExcelReport-*.csv와 동일 포맷)
    df = pd.read_csv(io.StringIO(res.text))
    print(f"[INFO] Export CSV rows: {len(df)}")
    return df


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)

    # 1) 날짜로 검색
    html, session, url = search_by_decision_date(START_DATE, END_DATE)

    # 2) Results per Page = 500 인 화면 가져오기
    html_500, url_500 = get_rpp500_page(session, url)

    # 3) Export to Excel CSV 다운로드
    df = download_export_csv(session, html_500, url_500)

    out_path = "data/raw_data.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[INFO] saved {len(df)} rows to {out_path}")
