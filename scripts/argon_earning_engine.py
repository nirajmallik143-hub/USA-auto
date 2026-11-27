import datetime
import json
import os
import subprocess
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

issue_num = os.environ.get("ISSUE_NUMBER", "").strip()
issue_title = os.environ.get("ISSUE_TITLE", "").strip()
issue_body = os.environ.get("ISSUE_BODY", "").strip()
earn_mode = os.environ.get("EARN_MODE", "").strip() or "micro_saas"
repo_name = os.environ["REPO_NAME"]
base_branch = os.environ.get("BASE_BRANCH") or "main"
checkout_url = os.environ.get("CHECKOUT_URL", "YOUR_REAL_CHECKOUT_URL")
sponsor_url = os.environ.get("SPONSOR_URL", "https://github.com/sponsors/Mallikgroup-for-Humanity")
today_tag = datetime.datetime.utcnow().strftime("%Y%m%d")

if issue_num:
    mission = f"Resolve Revenue/Feature Issue #{issue_num}: {issue_title}\nDetails:\n{issue_body}"
    branch_name = f"argon/earn-issue-{issue_num}"
else:
    mission = (
        f"Autonomous Daily Revenue Sprint (Mode: {earn_mode}) for {repo_name}.\n"
        "Build ONE concrete, high-value monetizable asset tailored to this repository:\n"
        "1. If micro_saas: Add a standalone, zero-dependency web/CLI micro-tool or API endpoint with usage tiers & Pro upgrade CTA.\n"
        "2. If digital_product: Generate a ready-to-sell prompt pack, automation template, or developer toolkit inside docs/products/ with a clear landing page.\n"
        "3. Update README.md (if needed) with a clean 'Pro Tools & Sponsorship' section linking to "
        f"{checkout_url} and {sponsor_url}."
    )
    branch_name = f"argon/earn-{today_tag}"

context_files = {}
for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".github", "venv", ".venv"}]
    for fname in sorted(files):
        if fname.startswith(".env"):
            continue
        if fname.endswith((".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".md", ".yml", ".yaml", ".sh")):
            fpath = os.path.join(root, fname).lstrip("./")
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                if len(content) <= 10000:
                    context_files[fpath] = content
            except Exception:
                pass

prompt = f"""
You are Argon, the Autonomous Venture & Revenue Architect for Mallik Group ({repo_name}).
Your goal is to turn this repository into a self-sustaining, ethical income-generating software & digital product asset.

Mission:
{mission}

Monetization Endpoints:
- Store / Checkout URL: {checkout_url}
- GitHub Sponsors URL: {sponsor_url}

Current Repository Files:
{json.dumps(context_files, indent=2)}

Rules:
- Never include fake testimonials, deceptive claims, or hardcoded secret keys.
- Every generated tool, landing page, or digital product must work out-of-the-box and provide immediate real value.
- Return ONLY valid JSON matching this exact schema:
{{
  "pr_title": "Concise revenue/feature PR title",
  "pr_body": "Business & technical summary explaining how this asset generates value or revenue",
  "comment_reply": "Short status update for the issue",
  "files": [
    {{
      "path": "relative/path/to/file",
      "content": "complete file content"
    }}
  ]
}}
"""

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config={"response_mime_type": "application/json"},
)

raw_text = response.text.strip().strip(chr(96)).removeprefix("json").strip()
plan = json.loads(raw_text)

files_to_write = plan.get("files", [])
if not files_to_write:
    print("Argon Earning Engine: no file changes needed.")
    raise SystemExit(0)

subprocess.run(["git", "config", "user.name", "argon-agent[bot]"], check=True)
subprocess.run(["git", "config", "user.email", "argon-agent[bot]@users.noreply.github.com"], check=True)
subprocess.run(["git", "checkout", "-B", branch_name], check=True)

for item in files_to_write:
    rel_path = item["path"].lstrip("/")
    if ".." in rel_path.split("/") or rel_path.startswith(".env"):
        continue
    parent = os.path.dirname(rel_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(rel_path, "w", encoding="utf-8") as f:
        f.write(item["content"])

subprocess.run(["git", "add", "."], check=True)
commit_msg = f"feat(earn): resolve #{issue_num}" if issue_num else f"feat(earn): autonomous revenue asset ({today_tag})"
subprocess.run(["git", "commit", "-m", commit_msg], check=True)
subprocess.run(["git", "push", "-u", "origin", branch_name, "--force"], check=True)

pr_title = plan.get("pr_title") or f"[Argon Earn] Autonomous Asset ({today_tag})"
closes_tag = f"\n\nCloses #{issue_num}" if issue_num else ""
pr_body = f"💰 **Argon Autonomous Earning Engine PR**\n\n{plan.get('pr_body', '')}{closes_tag}".strip()

pr_proc = subprocess.run(
    ["gh", "pr", "create", "--base", base_branch, "--head", branch_name, "--title", pr_title, "--body", pr_body],
    capture_output=True,
    text=True,
)
pr_url = pr_proc.stdout.strip()
print("Created Revenue PR:", pr_url)

if issue_num:
    reply = plan.get("comment_reply") or "Argon Earning Engine has built and submitted the requested asset."
    comment_body = f"💰 **Argon Autonomous Earning Engine**\n\n{reply}\n\n🔗 **Pull Request:** {pr_url}"
    subprocess.run(["gh", "issue", "comment", issue_num, "--body", comment_body], check=False)
