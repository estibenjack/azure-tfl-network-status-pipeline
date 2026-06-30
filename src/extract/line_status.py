import requests
import pandas as pd
from datetime import datetime, timezone
from src.utils.config import LINE_API_KEY, TFL_BASE_URL, TFL_MODES, AZURE_STORAGE_ACCOUNT_NAME, AZURE_STORAGE_ACCOUNT_KEY, ADLS_RAW_CONTAINER
import json
from azure.storage.filedatalake import DataLakeServiceClient


def fetch_line_status():
    # the line api accepts comma-separated modes
    url = f'{TFL_BASE_URL}/Line/Mode/{TFL_MODES}/Status'
    params = {"app_key": LINE_API_KEY}

    response = requests.get(url, params=params)
    response.raise_for_status()

    return response.json()


def transform_line_status(raw_json):
    """
    - prototypes the transformation logic locally for testing and development
    - in the actual pipeline, ADF handles this step. this function was written
      to validate the data shape and field extraction before building the
      equivalent logic in ADF Data Flow
    """
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


def upload_raw(raw_json, collected_at):
    # partition by date and time so files can be navigated easier over weeks of polling
    # ADLS sorts alphabetically, so zero-padding ensures chronological order
    file_path = f"raw/line-status/{collected_at.year}/{collected_at.month:02d}/{collected_at.day:02d}/{collected_at.hour:02d}{collected_at.minute:02d}.json"

    # serialise the raw api response untouched (acts as audit trail)
    # if transform logic ever has a bug, can reprocess from this file
    json_string = json.dumps(raw_json)

    # .dfs. endpoint instead of .blob. is required for ADLS gen 2 hierarchical namespace
    # .blob. would still work for basic storage but loses folder/path semantics
    connection_str = f"https://{AZURE_STORAGE_ACCOUNT_NAME}.dfs.core.windows.net"
    datalake_service_client = DataLakeServiceClient(connection_str,
                                                    # using account key here but in prod would use managed identity or scoped service principal
                                                    credential=AZURE_STORAGE_ACCOUNT_KEY)

    # filesystem client = the container (raw in this case)
    # file_client = specific path within the container
    file_system_client = datalake_service_client.get_file_system_client(
        ADLS_RAW_CONTAINER)
    file_client = file_system_client.get_file_client(file_path)

    # ADLS gen2 upload is 3-step process:
    # 1. create_file() - initialises the file at the path (overwrites if it exists!!)
    # 2. append_data() - stages the bytes at given offset
    # 3. flush_data() - commits the write (without this, file exists but is empty)
    json_bytes = json_string.encode('utf-8')
    file_client.create_file()
    file_client.append_data(json_bytes, offset=0, length=len(json_bytes))
    file_client.flush_data(len(json_bytes))


def main():
    collected_at = datetime.now(timezone.utc)
    raw = fetch_line_status()
    upload_raw(raw, collected_at)


if __name__ == "__main__":
    main()
