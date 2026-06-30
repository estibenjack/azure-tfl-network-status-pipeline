import requests
import pandas as pd
from datetime import datetime, timezone
from src.utils.config import LINE_API_KEY, TFL_BASE_URL, TFL_MODES


def fetch_line_status():
    # the line api accepts comma-separated modes
    url = f'{TFL_BASE_URL}/Line/Mode/{TFL_MODES}/Status'
    params = {"app_key": LINE_API_KEY}

    response = requests.get(url, params=params)
    response.raise_for_status()

    return response.json()


def transform_line_status(raw_json):
    results = []
    collected_at_ts = datetime.now(timezone.utc)

    for line in raw_json:
        line_id = line['id']
        line_name = line['name']
        mode_name = line['modeName']
        for status in line['lineStatuses']:
            status_dict = {
                'line_id': line_id,
                'line_name': line_name,
                'mode_name': mode_name,
                'status_severity': status['statusSeverity'],
                'status_severity_description': status['statusSeverityDescription'],
                # using .get() because reason is empty on good service lines -- None translates to NULL in the db serving layer
                'reason': status.get('reason', None),
                'collected_at': collected_at_ts
            }
            results.append(status_dict)

    results_df = pd.DataFrame(results)

    return results_df


# def upload_raw(df, timestamp):
    # TODO: write to ADLS raw zone, partitioned by date/hour
    pass


# def main():
    # TODO: wire up fetch -> transform -> upload
    pass


if __name__ == "__main__":
    # main()
    raw = fetch_line_status()
    df = transform_line_status(raw)
    print(df)
    print(df.dtypes)
