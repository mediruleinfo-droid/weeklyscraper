import os
import requests
import pandas as pd
from bs4 import BeautifulSoup

BASE_URL = "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmnsimplesearch.cfm"
START_DATE = "11/16/2025"
END_DATE   = "11/22/2025"

def fetch_510k_decision_range(start_date: str, end_date: str) -> pd.DataFrame:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    data = {
        "BasicSearch": "Decision Date",
        "DecisionFrom": start_date,
        "DecisionTo": end_date,
        "Sort": "DecisionDate",
        "StartRec": "1",
        "MaxRec": "500",
        "ShowResult": "YES",
    }
    res = session.post(BASE_URL, data=data, timeout=60)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.find("table")
    if table is None:
        print("No table found")
        return pd.DataFrame()

    dfs = pd.read_html(str(table))
    if not dfs:
        print("No tables parsed by pandas")
        return pd.DataFrame()

    return dfs[0]

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    df = fetch_510k_decision_range(START_DATE, END_DATE)
    df.to_csv("data/raw_data.csv", index=False, encoding="utf-8-sig")
    print(f"saved {len(df)} rows")
