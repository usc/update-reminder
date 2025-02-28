import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import argparse
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Get the script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Load targets from file
def load_targets_from_file(filename):
    try:
        with open(filename, "r") as file:
            targets = [line.strip() for line in file if line.strip()]
        return targets
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return []

# Load cache from file
def load_cache(cache_file):
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as file:
                return json.load(file)
        except (json.JSONDecodeError, IOError):
            print("Error loading cache file. Starting with an empty cache.")
    return {}

# Save cache to file
def save_cache(cache, cache_file):
    try:
        with open(cache_file, "w") as file:
            json.dump(cache, file, indent=4)
    except IOError as e:
        print(f"Error saving cache: {e}")

# Check if a target needs checking
def is_check_needed(cache):
    today = datetime.now(timezone.utc).date()
    today_str = today.strftime("%Y-%m-%d")
    last_checked = cache.get("last_checked")

    if last_checked:
        last_checked_date = datetime.strptime(last_checked, "%Y-%m-%d").date()
        if last_checked_date == today:
            print(f"{today_str} - Targets update already checked today. No new checks performed.")
            return False

    # update last_checked today
    cache["last_checked"] = today_str
    return True

# Check GitHub repository releases
def check_repo_releases(repo, token, days, cache):
    base_url = "https://api.github.com/repos/"
    headers = {"Authorization": f"token {token}"} if token else {}
    threshold_date = datetime.now(timezone.utc) - timedelta(days=days)

    #print(f"Checking GitHub repository: {repo} ...")
    try:
        response = requests.get(f"{base_url}{repo}/releases/latest", headers=headers)
        response.raise_for_status()
        release = response.json()

        if release["prerelease"] or release["draft"]:
            return None  # Skip pre-releases and drafts

        version = release["tag_name"].lower()
        if "alpha" in version or "beta" in version:
            return None  # Skip alpha or beta versions

        published_at = datetime.strptime(release["published_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if published_at > threshold_date:
            if cache.get(repo) == version:
                return None  # Skip if version already notified

            cache[repo] = version
            return {"repo": repo, "version": version, "published_at": published_at, "html_url": release["html_url"]}

    except requests.exceptions.RequestException as e:
        print(f"Error checking releases for {repo}: {e}")
        return None

# Check Jenkins build
def check_jenkins_build(job_url, cache):
    #print(f"Checking Jenkins job: {job_url} ...")
    api_url = f"{job_url.rstrip('/')}/lastSuccessfulBuild/api/json"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        last_build = response.json()

        if not last_build:
            print(f"Warning: No successful builds found for {job_url}.")
            return None

        build_number = last_build.get("number")
        build_url = last_build.get("url")
        build_timestamp = last_build.get("timestamp")  # Milliseconds timestamp
        build_date = datetime.fromtimestamp(build_timestamp / 1000, tz=timezone.utc).replace(microsecond=0)

        cached_build = cache.get(job_url)
        if cached_build == build_number:
            return None

        cache[job_url] = build_number
        return {"job_url": job_url, "build_number": build_number, "build_date": build_date, "build_url": build_url}

    except requests.exceptions.RequestException as e:
        print(f"Error checking Jenkins job {job_url}: {e}")
        return None

# Main checking logic
def check_targets(targets, cache, github_token=None, days=7):
    recent_updates = []

    for target in targets:
        if target.startswith("https://"):  # Detect Jenkins job
            result = check_jenkins_build(target, cache)
            if result:
                recent_updates.append(result)
        else:  # Detect GitHub repository
            result = check_repo_releases(target, github_token, days, cache)
            if result:
                recent_updates.append(result)

    return recent_updates

# Format update message
def format_update_message(update):
    if "build_number" in update:
        return (
            f"Jenkins Job: {update['job_url']} - Build #{update['build_number']} "
            f"(URL: {update['build_url']}, Date: {update['build_date']})"
        )
    else:
        return (
            f"GitHub Repo: {update['repo']} - Version: {update['version']} "
            f"(URL: {update['html_url']}, Published: {update['published_at']})"
        )

# Write updates to a file in append mode
def write_updates_to_file(updates, file_path):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Current date and time
    try:
        with open(file_path, "a") as file:
            for update in updates:
                message = format_update_message(update)
                file.write(f"{current_time} - {message}\n")
    except IOError as e:
        print(f"Error writing updates to file {file_path}: {e}")

# Send updates via Telegram
def send_updates_via_telegram(updates, bot_token, chat_id):
    if bot_token and chat_id:
        base_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        for update in updates:
            message = format_update_message(update)
            payload = {"chat_id": chat_id, "text": message}
            try:
                response = requests.post(base_url, data=payload)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"Error sending update via Telegram: {e}")

# Send updates via email
def send_updates_via_email(updates, email_config):
    if not all(email_config.values()):
        return

    smtp_server = email_config["SMTP_SERVER"]
    smtp_port = email_config["SMTP_PORT"]
    sender_email = email_config["SENDER_EMAIL"]
    receiver_email = email_config["RECEIVER_EMAIL"]
    password = email_config["EMAIL_PASSWORD"]
    cc_sender = email_config.get("CC_SENDER", "true").lower() == "true"

    subject = "Recent Updates Notification"
    body = "\n".join([format_update_message(update) for update in updates])

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    if cc_sender:
        msg["Cc"] = sender_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    recipients = [receiver_email]
    if cc_sender:
        recipients.append(sender_email)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, recipients, msg.as_string())
    except Exception as e:
        print(f"Error sending email: {e}")

# Main function
if __name__ == "__main__":
    # load env
    dotenv_path = os.path.join(SCRIPT_DIR, ".env")
    load_dotenv(dotenv_path)

    token = os.getenv("GITHUB_TOKEN")
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    email_config = {
        "SMTP_SERVER": os.getenv("SMTP_SERVER"),
        "SMTP_PORT": os.getenv("SMTP_PORT"),
        "SENDER_EMAIL": os.getenv("SENDER_EMAIL"),
        "RECEIVER_EMAIL": os.getenv("RECEIVER_EMAIL"),
        "EMAIL_PASSWORD": os.getenv("EMAIL_PASSWORD"),
        "CC_SENDER": os.getenv("CC_SENDER", "true")
    }

    parser = argparse.ArgumentParser(description="Check recent updates from GitHub repositories and Jenkins jobs.")
    parser.add_argument(
        "--file",
        default=os.path.join(SCRIPT_DIR, "targets.txt"),
        help="Path to the file containing repository or Jenkins job list (default: targets.txt)."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to check for recent updates (default: 7)."
    )
    parser.add_argument(
        "--cache",
        default=os.path.join(SCRIPT_DIR, "cache.json"),
        help="Path to the cache file (default: cache.json)."
    )
    parser.add_argument(
        "--updates",
        default=os.path.join(SCRIPT_DIR, "updates.txt"),
        help="Path to the updates file (default: updates.txt in the script directory)."
    )

    args = parser.parse_args()

    targets = load_targets_from_file(args.file)
    if not targets:
        print("No targets found. Please check your input file.")
    else:
        cache = load_cache(args.cache)
        if is_check_needed(cache):
            recent_updates = check_targets(targets, cache, token, args.days)
            save_cache(cache, args.cache)

            current_date = datetime.now().strftime("%Y-%m-%d")
            if recent_updates:
                print(f"{current_date} - Recent updates:")
                for update in recent_updates:
                    print(format_update_message(update))

                # Write updates to updates.txt
                write_updates_to_file(recent_updates, args.updates)

                # Send updates via Telegram
                send_updates_via_telegram(recent_updates, telegram_bot_token, telegram_chat_id)

                # Send updates via Email
                send_updates_via_email(recent_updates, email_config)
            else:
                print(f"{current_date} - Targets no new updates.")
