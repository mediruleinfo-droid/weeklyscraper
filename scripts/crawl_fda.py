import os
import io
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

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
        "DecisionDateFrom": start_date,
        "DecisionDateTo": end_date,
        "SortColumn": "dd_desc",  # Decision Date (descending)
        "Search": "Search",
    }

    print(f"[INFO] Requesting search HTML {start_date} ~ {end_date}")
    res = session.post(SEARCH_URL, data=data, timeout=60)
    res.raise_for_status()
    return res.text, session, res.url


def build_rpp500_url(url: str) -> str:
    """
    검색 결과 URL 의 쿼리스트링을 분석해서,
    한 페이지에 최대 500개가 보이도록 PAGENUM(또는 rpp)을 조정한 URL을 만든다.
    (실제 파라미터 이름이 다르면 여기서만 맞춰주면 됨)
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    # FDA HTML에서 PAGENUM=10 으로 보이는 부분을 500으로 바꾸는 전략.
    # (만약 Network 탭에서 rpp 라는 파라미터를 확인하면 아래에 추가로 설정)
    if "PAGENUM" in qs:
        qs["PAGENUM"] = ["500"]
    else:
        qs["PAGENUM"] = ["500"]

    # start_search 는 1에서 시작
    qs["start_search"] = ["1"]

    new_query = urlencode(qs, doseq=True)
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)


def get_rpp500_page(session: requests.Session, url: str):
    """
    rpp=500(또는 PAGENUM=500) 이 반영된 URL로 GET 요청을 보내
    한 페이지에 모든 결과가 보이는 HTML을 가져온다.
    """
    rpp_url = build_rpp500_url(url)
    print(f"[INFO] Requesting rpp=500 page: {rpp_url}")
    res = session.get(rpp_url, timeout=60)
    res.raise_for_status()
    return res.text, res.url


def download_export_csv(session: requests.Session, html: str, base_url: str) -> pd.DataFrame:
    """
    결과 페이지 HTML에서 title='Export to Excel' 링크를 찾아 CSV를 내려받아 DataFrame 으로 반환한다.
    """
    soup = BeautifulSoup(html, "html.parser")
    link = soup.find("a", {"title": "Export to Excel"})
    if link is None:
        raise RuntimeError("Cannot find 'Export to Excel' link on the page.")

    href = link.get("href")
    if not href:
        raise RuntimeError("Export to Excel link has no href.")

    export_url = urljoin(base_url, href)
    print(f"[INFO] Downloading CSV from: {export_url}")
    res = session.get(export_url, timeout=60)
    res.raise_for_status()

    # 응답은 CSV 텍스트라고 가정 (직접 받은 PMNExcelReport-*.csv 와 동일 포맷)
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
