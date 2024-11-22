import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import argparse
import json
import os

# 从文件读取仓库列表
def load_repos_from_file(filename="repo.txt"):
    try:
        with open(filename, "r") as file:
            repos = [line.strip() for line in file if line.strip()]
        return repos
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return []

# 加载缓存文件
def load_cache(cache_file="cache.json"):
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as file:
                return json.load(file)
        except (json.JSONDecodeError, IOError):
            print("Error loading cache file. Starting with an empty cache.")
    return {}

# 保存缓存文件
def save_cache(cache, cache_file="cache.json"):
    try:
        with open(cache_file, "w") as file:
            json.dump(cache, file, indent=4)
    except IOError as e:
        print(f"Error saving cache: {e}")

# 检查是否需要进行新的检查
def is_check_needed(cache, cache_file="cache.json"):
    today = datetime.now(timezone.utc).date()
    last_checked = cache.get("last_checked")

    if last_checked:
        last_checked_date = datetime.strptime(last_checked, "%Y-%m-%d").date()
        if last_checked_date == today:
            print("Already checked today. No new checks performed.")
            return False

    # 更新最后检查日期为今天
    cache["last_checked"] = today.strftime("%Y-%m-%d")
    save_cache(cache, cache_file)
    return True

# 检查仓库最近发布的版本
def check_repo_releases(repos, token, days=7, cache_file="cache.json"):
    base_url = "https://api.github.com/repos/"
    headers = {"Authorization": f"token {token}"} if token else {}
    threshold_date = datetime.now(timezone.utc) - timedelta(days=days)
    recent_releases = []

    # 加载缓存
    cache = load_cache(cache_file)

    for repo in repos:
        try:
            # 获取 releases 列表
            response = requests.get(f"{base_url}{repo}/releases", headers=headers)
            response.raise_for_status()
            releases = response.json()

            # 筛选有效的版本
            for release in releases:
                if release["prerelease"] or release["draft"]:
                    continue  # 跳过 pre-release 和 draft 版本

                # 跳过包含 alpha 或 beta 的版本
                version = release["tag_name"].lower()
                if "alpha" in version or "beta" in version:
                    continue

                # 检查发布日期
                published_at = datetime.strptime(release["published_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if published_at > threshold_date:
                    # 检查缓存
                    repo_cache = cache.get(repo, [])
                    if version in repo_cache:
                        continue  # 如果版本已提示过，则跳过

                    recent_releases.append((repo, version, published_at))
                    repo_cache.append(version)  # 记录已提示过的版本
                    cache[repo] = repo_cache

        except requests.exceptions.RequestException as e:
            print(f"Error checking releases for {repo}: {e}")

    # 保存更新后的缓存
    save_cache(cache, cache_file)

    return recent_releases

# 主函数
if __name__ == "__main__":
    # 加载 .env 文件
    load_dotenv(".env")

    # 从 .env 文件获取 GitHub token
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN not found in .env file.")
        exit(1)

    # 设置命令行参数解析
    parser = argparse.ArgumentParser(description="Check recent releases from GitHub repositories.")
    parser.add_argument(
        "--file",
        default="repo.txt",
        help="Path to the file containing repository list (default: repo.txt)."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to check for recent releases (default: 7)."
    )
    parser.add_argument(
        "--cache",
        default="cache.json",
        help="Path to the cache file (default: cache.json)."
    )

    args = parser.parse_args()

    # 加载仓库列表
    repo_list = load_repos_from_file(args.file)
    if not repo_list:
        print("No repositories found. Please check your input file.")
    else:
        # 加载缓存并检查是否需要新检查
        cache = load_cache(args.cache)
        if is_check_needed(cache, args.cache):
            recent_updates = check_repo_releases(repo_list, token, args.days, args.cache)

            if recent_updates:
                print(f"Repositories with new releases in the last {args.days} days:")
                for repo, version, published_at in recent_updates:
                    print(f"{repo} - Version: {version} (Published: {published_at})")
            else:
                print("No new releases since the last check.")
