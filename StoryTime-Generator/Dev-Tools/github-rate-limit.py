import os
import requests
import time

def get_github_rate_limit(token=None):
    url = "https://api.github.com/rate_limit"
    headers = {}
    if token is None:
        token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch rate limit info: {response.status_code} {response.text}")
        return
    data = response.json()
    core = data.get("resources", {}).get("core", {})
    search = data.get("resources", {}).get("search", {})
    print("GitHub API Rate Limit Status:")
    print(f"  Core: {core.get('remaining', '?')}/{core.get('limit', '?')} remaining, resets at {time.ctime(core.get('reset', 0))}")
    print(f"  Search: {search.get('remaining', '?')}/{search.get('limit', '?')} remaining, resets at {time.ctime(search.get('reset', 0))}")
    print("  (Other categories available in response)")
    # print everything for debugging
    print("\nFull Rate Limit Response:")
    print(data)

if __name__ == "__main__":
    get_github_rate_limit()
