import requests
import sys
from collections import defaultdict
from datetime import datetime
from os import environ
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import numpy as np

load_dotenv()

OWNER = "daytonaio"
REPO = "docs"

def fetch_pull_requests(token, state, date_field, username, per_page=100):
    headers = {"Authorization": f"token {token}"}
    prs_list = []
    page = 1

    while True:
        url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls"
        params = {"state": state, "per_page": per_page, "page": page}
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(
                f"Failed to fetch pull requests. Status code: {response.status_code}"
            )
            sys.exit(1)

        prs = response.json()
        if not prs:
            break

        for pr in prs:
            if pr.get("user", {}).get("login") != username:
                continue

            if state == "closed" and date_field == "merged_at":
                if pr.get("merged_at"):
                    prs_list.append(
                        (pr.get("number"), pr.get("title"), pr.get("merged_at"))
                    )
            else:
                prs_list.append(
                    (pr.get("number"), pr.get("title"), pr.get(date_field))
                )
        page += 1

    return prs_list

def group_prs_by_month(prs):
    grouped = defaultdict(list)
    for pr in prs:
        pr_date = pr[2]
        try:
            dt = datetime.fromisoformat(pr_date.rstrip("Z"))
        except Exception as e:
            print(f"Error parsing date {pr_date}: {e}")
            continue
        month_key = dt.strftime("%Y-%m")
        grouped[month_key].append(pr)
    return grouped

def calculate_monthly_pull_requests(grouped_prs):
    counts = {}
    for month, prs in grouped_prs.items():
        counts[month] = len(prs)
    return counts

def plot_pull_requests(merged_counts, open_counts, img_filepath="pull-requests.png"):
    all_months = sorted(set(merged_counts.keys()) | set(open_counts.keys()),
                        key=lambda m: datetime.strptime(m, "%Y-%m"))

    merged_vals = [merged_counts.get(month, 0) for month in all_months]
    open_vals = [open_counts.get(month, 0) for month in all_months]

    x = np.arange(len(all_months))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - width/2, merged_vals, width, label='Merged', color='green')
    ax.bar(x + width/2, open_vals, width, label='Open', color='gray')

    ax.set_ylabel('Count')
    ax.set_title('Monthly Pull Requests')
    ax.set_xticks(x)
    ax.set_xticklabels(all_months, rotation=45)
    ax.legend()

    fig.tight_layout()
    plt.savefig(img_filepath, dpi=300)
    print(f"Graph saved as {img_filepath}")

def markdown_report(merged_groups, open_groups, md_filepath="README.md"):
    all_months = set(merged_groups.keys()) | set(open_groups.keys())
    sorted_months = sorted(
        all_months, key=lambda m: datetime.strptime(m, "%Y-%m"), reverse=True
    )
    report_lines = []

    report_lines.append("![Pull Requests](pull-requests.png)")

    for month in sorted_months:
        report_lines.append(f"\n## {month}\n")

        if month in merged_groups:
            report_lines.append("### Merged Pull Requests\n")
            merged_sorted = sorted(merged_groups[month], key=lambda pr: pr[2])
            for pr in merged_sorted:
                report_lines.append(
                    f"- [#{pr[0]}](https://github.com/{OWNER}/{REPO}/pull/{pr[0]}): {pr[1]} (merged at: {pr[2]})"
                )

        if month in open_groups:
            report_lines.append("\n### Open Pull Requests\n")
            open_sorted = sorted(open_groups[month], key=lambda pr: pr[2])
            for pr in open_sorted:
                report_lines.append(
                    f"- [#{pr[0]}](https://github.com/{OWNER}/{REPO}/pull/{pr[0]}): {pr[1]} (created at: {pr[2]})"
                )

    with open(md_filepath, "w", encoding="utf-8") as md_file:
        md_file.write("\n".join(report_lines))
    print(f"Markdown report written to {md_filepath}")

def print_monthly_reports(merged_groups, open_groups):
    all_months = set(merged_groups.keys()) | set(open_groups.keys())
    sorted_months = sorted(
        all_months, key=lambda m: datetime.strptime(m, "%Y-%m"), reverse=True
    )

    for month in sorted_months:
        print(f"\n=== {month} ===")

        if month in merged_groups:
            print("Merged Pull Requests")
            merged_sorted = sorted(merged_groups[month], key=lambda pr: pr[2])
            for pr in merged_sorted:
                print(f"(#{pr[0]}) {pr[1]} (merged at: {pr[2]})")

        if month in open_groups:
            print("Open Pull Requests")
            open_sorted = sorted(open_groups[month], key=lambda pr: pr[2])
            for pr in open_sorted:
                print(f" #{pr[0]}: {pr[1]} (created at: {pr[2]})")

def main():
    token = environ.get("GITHUB_TOKEN")
    username = environ.get("GITHUB_USERNAME")

    if not token or not username:
        print("Missing GITHUB_TOKEN and/or GITHUB_USERNAME in environment.")
        sys.exit(1)

    merged_prs = fetch_pull_requests(
        token, state="closed", date_field="merged_at", username=username
    )
    open_prs = fetch_pull_requests(
        token, state="open", date_field="created_at", username=username
    )

    merged_groups = group_prs_by_month(merged_prs)
    open_groups = group_prs_by_month(open_prs)

    print_monthly_reports(merged_groups, open_groups)
    markdown_report(merged_groups, open_groups)

    merged_counts = calculate_monthly_pull_requests(merged_groups)
    open_counts = calculate_monthly_pull_requests(open_groups)

    plot_pull_requests(merged_counts, open_counts)

if __name__ == "__main__":
    main()
