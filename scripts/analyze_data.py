import pandas as pd
import json
import os

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    df = pd.read_csv("data/raw_data.csv")
    analysis = {
        "total_clearances": int(len(df)),
    }
    with open("data/analysis.json", "w") as f:
        json.dump(analysis, f, indent=2)
    print(analysis)
