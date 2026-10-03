# Create YouTube OAuth tokens on an Android phone with Replit

This guide is for someone using a Redmi or another Android phone who cannot run Python on a computer. Replit runs the small Python program for you in a browser. You will use Google to approve access to your YouTube channel, then save the resulting JSON as GitHub secrets.

**Keep both JSON files private.** Never paste them into a public chat, a GitHub issue, or a file committed to this repository. The token lets the workflow access your channel.

## 1. Prepare Google Cloud

1. In Google Cloud Console, select the project for your channel and enable **YouTube Data API v3**.
2. In **Google Auth Platform** (or the OAuth consent screen settings), set up the app. Choose **External** if asked, and add the Google account that owns your YouTube channel as a test user.
3. Create an OAuth client with application type **Web application**. A Desktop app client will not work for this Replit callback.
4. First create your Replit project as described below so you can see its public web domain. In the OAuth client, add this exact value under **Authorized redirect URIs**, replacing the example domain with your Replit domain:

   `https://YOUR-REPLIT-DOMAIN/oauth2callback`

   For example, if Replit shows `abc123.replit.dev`, enter `https://abc123.replit.dev/oauth2callback`. The address must match exactly.
5. Download the Web application client JSON to your phone, or keep its full contents available to paste into Replit. It usually has a top-level `"web"` field.

## 2. Create the Replit program

1. Open [replit.com](https://replit.com) in your phone browser, sign in, and create a new **Python** project.
2. Open the project in a new browser tab (Replit may call this **Open in new tab**) and note the domain shown in its address. Use that same domain in the Google redirect URI above.
3. In Replit, open **Secrets** (the lock icon, sometimes under **Tools**) and add:
   - Key: `YOUTUBE_CLIENT_SECRETS_JSON`
   - Value: the complete contents of the downloaded Web application client JSON
4. Open the Replit **Shell** and install the two packages:

   ```bash
   pip install Flask google-auth-oauthlib
   ```

5. Open `main.py`, remove its sample contents, and paste this complete program:

   ```python
   import html
   import json
   import os
   import secrets

   from flask import Flask, redirect, request, session
   from google_auth_oauthlib.flow import Flow

   app = Flask(__name__)
   app.secret_key = secrets.token_hex(32)
   app.config.update(
       SESSION_COOKIE_SECURE=True,
       SESSION_COOKIE_HTTPONLY=True,
       SESSION_COOKIE_SAMESITE="Lax",
   )

   SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


   def redirect_uri():
       domain = os.environ.get("REPLIT_DEV_DOMAIN", "").strip()
       domain = domain.removeprefix("https://").removeprefix("http://").strip("/")
       if not domain:
           raise RuntimeError(
               "Replit did not provide REPLIT_DEV_DOMAIN. Add it in Replit Secrets "
               "using your project domain, without https://."
           )
       return f"https://{domain}/oauth2callback"


   def new_flow(state=None):
       client_json = json.loads(os.environ["YOUTUBE_CLIENT_SECRETS_JSON"])
       if "web" not in client_json:
           raise ValueError(
               "The client JSON must be for a Google OAuth Web application."
           )
       return Flow.from_client_config(
           client_json,
           scopes=SCOPES,
           state=state,
           redirect_uri=redirect_uri(),
       )


   @app.get("/")
   def start():
       flow = new_flow()
       auth_url, state = flow.authorization_url(
           access_type="offline",
           include_granted_scopes="true",
           prompt="consent",
       )
       session["oauth_state"] = state
       return redirect(auth_url)


   @app.get("/oauth2callback")
   def finish():
       state = session.pop("oauth_state", None)
       if not state:
           return "This sign-in link expired. Go back to the Replit app and try again.", 400

       flow = new_flow(state=state)
       flow.fetch_token(authorization_response=request.url)
       credentials = flow.credentials
       if not credentials.refresh_token:
           return (
               "Google did not return a refresh token. Try again and approve access. "
               "If needed, remove this app's access from your Google Account first.",
               400,
           )

       token_json = html.escape(credentials.to_json())
       return (
           "<h1>Your YouTube token is ready</h1>"
           "<p>Copy all the JSON below. Keep it private.</p>"
           f"<pre>{token_json}</pre>"
       )


   if __name__ == "__main__":
       print(f"Add this exact URL as Google's authorized redirect URI: {redirect_uri()}")
       app.run(host="0.0.0.0", port=3000, debug=False)
   ```

6. In Replit **Secrets**, add `REPLIT_DEV_DOMAIN` only if Replit has not already provided it. Its value is the domain from the Replit project address, without `https://` or a path (for example, `abc123.replit.dev`).
7. Press **Run**. Open the web page for the running Replit project. Sign in to Google with the account that owns your channel and approve the YouTube upload permission. Replit displays the token JSON after approval.
8. Copy the **entire** JSON shown on the page, from the opening `{` to the closing `}`. Do not post it anywhere. If the program reports that no refresh token was returned, try the sign-in again and approve access; if necessary, remove the app's access from your Google Account first.

## 3. Save both GitHub secrets

Open your repository on GitHub, then go to **Settings → Secrets and variables → Actions → Secrets → New repository secret**. Add each secret separately:

1. Name: `YOUTUBE_CLIENT_SECRETS_JSON`  
   Value: the complete contents of the Web application client JSON you downloaded from Google Cloud.
2. Name: `YOUTUBE_TOKEN_JSON`  
   Value: the complete token JSON displayed by the Replit program.

Use **Secrets**, not **Variables**, for these two values. Do not put either JSON file in the repository. After saving the secrets, stop the Replit program and remove its `YOUTUBE_CLIENT_SECRETS_JSON` secret if you no longer need it.

## 4. Turn off dry-run mode

In GitHub, open **Settings → Secrets and variables → Actions → Variables → New repository variable**. Add:

- Name: `DRY_RUN_UPLOAD`
- Value: `false`

The workflow defaults to dry-run mode (`true`) when this variable is missing. With `false`, it can make real uploads.

## 5. Run the workflow once

1. Open the repository's **Actions** tab.
2. Choose **Daily USA Kids Videos**.
3. Choose **Run workflow**, select the branch containing the workflow, and confirm **Run workflow**.
4. Open the new run to see whether it completed. If it fails, open its **logs** artifact for details.

**Important:** With dry-run disabled, this is a real run, not a pretend test. It can upload videos to your channel. Make sure you are ready for the workflow's daily batch before starting it.

## Important token and app notes

- While the Google OAuth app is in **Testing**, YouTube tokens can stop refreshing after 7 days. For ongoing automation, change the app's publishing status to **In production** in Google Auth Platform. Google may require verification for the requested YouTube permission; follow any notice shown in Cloud Console.
- Production status does not mean a token can never expire. If uploads stop working, create a fresh token with this guide and replace `YOUTUBE_TOKEN_JSON` in GitHub.
- Keep the Replit project and all OAuth JSON private. Do not commit the client JSON or token JSON, and do not share a screenshot of the token page.
