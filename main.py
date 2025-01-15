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
REPOS = ["docs", "enterprise-docs"]

def fetch_pull_requests(token, repo, state, date_field, username, per_page=100):
    headers = {"Authorization": f"token {token}"}
    prs_list = []
    page = 1

    while True:
        url = f"https://api.github.com/repos/{OWNER}/{repo}/pulls"
        params = {"state": state, "per_page": per_page, "page": page}
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Failed to fetch pull requests for {repo}. Status code: {response.status_code}")
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
                        (repo, pr.get("number"), pr.get("title"), pr.get("merged_at"))
                    )
            else:
                prs_list.append(
                    (repo, pr.get("number"), pr.get("title"), pr.get(date_field))
                )
        page += 1

    return prs_list

def group_prs_by_month(prs):
    grouped = defaultdict(list)
    for pr in prs:
        pr_date = pr[3]
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

def plot_combined_pull_requests(merged_counts_oss, open_counts_oss, 
                                merged_counts_ent, open_counts_ent, img_filepath="pull-requests.png"):
    all_months = sorted(
        set(merged_counts_oss.keys()) | set(open_counts_oss.keys()) |
        set(merged_counts_ent.keys()) | set(open_counts_ent.keys()),
        key=lambda m: datetime.strptime(m, "%Y-%m")
    )

    merged_vals_oss = [merged_counts_oss.get(month, 0) for month in all_months]
    open_vals_oss = [open_counts_oss.get(month, 0) for month in all_months]
    merged_vals_ent = [merged_counts_ent.get(month, 0) for month in all_months]
    open_vals_ent = [open_counts_ent.get(month, 0) for month in all_months]

    x = np.arange(len(all_months))
    width = 0.2

    fig, ax = plt.subplots(figsize=(12, 8))
    ax.bar(x - width * 1.5, merged_vals_oss, width, label='OSS Merged', color='darkgreen')
    ax.bar(x - width / 2, open_vals_oss, width, label='OSS Open', color='lightgreen')
    ax.bar(x + width / 2, merged_vals_ent, width, label='Enterprise Merged', color='darkblue')
    ax.bar(x + width * 1.5, open_vals_ent, width, label='Enterprise Open', color='lightblue')

    ax.set_ylabel('Count')
    ax.set_title('Monthly Pull Requests (OSS vs Enterprise)')
    ax.set_xticks(x)
    ax.set_xticklabels(all_months, rotation=45)
    ax.legend()

    fig.tight_layout()
    plt.savefig(img_filepath, dpi=300)
    print(f"Graph saved as {img_filepath}")

def markdown_report(merged_groups_oss, open_groups_oss, 
                    merged_groups_ent, open_groups_ent, md_filepath="README.md"):
    all_months = set(merged_groups_oss.keys()) | set(open_groups_oss.keys()) | \
                 set(merged_groups_ent.keys()) | set(open_groups_ent.keys())
    sorted_months = sorted(
        all_months, key=lambda m: datetime.strptime(m, "%Y-%m"), reverse=True
    )
    report_lines = []

    report_lines.append("![Pull Requests](pull-requests.png)")

    for month in sorted_months:
        report_lines.append(f"\n## {month}\n")

        if month in merged_groups_oss:
            report_lines.append("### OSS Merged Pull Requests\n")
            for pr in sorted(merged_groups_oss[month], key=lambda pr: pr[3]):
                report_lines.append(
                    f"- [#{pr[1]}](https://github.com/{OWNER}/{pr[0]}/pull/{pr[1]}): {pr[2]} (merged at: {pr[3]})"
                )

        if month in open_groups_oss:
            report_lines.append("\n### OSS Open Pull Requests\n")
            for pr in sorted(open_groups_oss[month], key=lambda pr: pr[3]):
                report_lines.append(
                    f"- [#{pr[1]}](https://github.com/{OWNER}/{pr[0]}/pull/{pr[1]}): {pr[2]} (created at: {pr[3]})"
                )

        if month in merged_groups_ent:
            report_lines.append("\n### Enterprise Merged Pull Requests\n")
            for pr in sorted(merged_groups_ent[month], key=lambda pr: pr[3]):
                report_lines.append(
                    f"- [#{pr[1]}](https://github.com/{OWNER}/{pr[0]}/pull/{pr[1]}): {pr[2]} (merged at: {pr[3]})"
                )

        if month in open_groups_ent:
            report_lines.append("\n### Enterprise Open Pull Requests\n")
            for pr in sorted(open_groups_ent[month], key=lambda pr: pr[3]):
                report_lines.append(
                    f"- [#{pr[1]}](https://github.com/{OWNER}/{pr[0]}/pull/{pr[1]}): {pr[2]} (created at: {pr[3]})"
                )

    with open(md_filepath, "w", encoding="utf-8") as md_file:
        md_file.write("\n".join(report_lines))
    print(f"Markdown report written to {md_filepath}")

def main():
    token = environ.get("GITHUB_TOKEN")
    username = environ.get("GITHUB_USERNAME")

    if not token or not username:
        print("Missing GITHUB_TOKEN and/or GITHUB_USERNAME in environment.")
        sys.exit(1)

    merged_prs_oss = []
    open_prs_oss = []
    merged_prs_ent = []
    open_prs_ent = []

    for repo in REPOS:
        merged_prs = fetch_pull_requests(token, repo, state="closed", date_field="merged_at", username=username)
        open_prs = fetch_pull_requests(token, repo, state="open", date_field="created_at", username=username)

        if repo == "docs":
            merged_prs_oss.extend(merged_prs)
            open_prs_oss.extend(open_prs)
        elif repo == "enterprise-docs":
            merged_prs_ent.extend(merged_prs)
            open_prs_ent.extend(open_prs)

    merged_groups_oss = group_prs_by_month(merged_prs_oss)
    open_groups_oss = group_prs_by_month(open_prs_oss)
    merged_groups_ent = group_prs_by_month(merged_prs_ent)
    open_groups_ent = group_prs_by_month(open_prs_ent)

    markdown_report(merged_groups_oss, open_groups_oss, merged_groups_ent, open_groups_ent)

    merged_counts_oss = calculate_monthly_pull_requests(merged_groups_oss)
    open_counts_oss = calculate_monthly_pull_requests(open_groups_oss)
    merged_counts_ent = calculate_monthly_pull_requests(merged_groups_ent)
    open_counts_ent = calculate_monthly_pull_requests(open_groups_ent)

    plot_combined_pull_requests(merged_counts_oss, open_counts_oss, merged_counts_ent, open_counts_ent)

if __name__ == "__main__":
    main()
