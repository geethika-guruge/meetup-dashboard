# Meetup API Authentication

Simple Python script to authenticate with Meetup API and fetch data.

## Setup

1. **Register your app** at [meetup.com/api/oauth_consumers](https://www.meetup.com/api/oauth_consumers/)
   - Set redirect URI to: `http://example.com/callback`
   - Note your Client ID and Client Secret

2. **Install dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Set environment variables**:
   ```bash
   export MEETUP_CLIENT_ID="your_client_id_here"
   export MEETUP_CLIENT_SECRET="your_client_secret_here"
   export MEETUP_PRO_URLNAME="your_pro_network_urlname"
   ```

## Usage

```bash
python meetup_auth.py
```

**Steps:**
1. Script displays authorization URL
2. Visit URL in browser and authorize
3. Copy authorization code from callback URL
4. Paste code into script
5. Script fetches your profile and events
6. Data saved to `meetup_data.json`

## Example Output

```
1. Visit this URL to authorize the app:
https://secure.meetup.com/oauth2/authorize?client_id=...

2. Enter the authorization code from the callback URL: abc123

✓ Authentication successful!
Hello, John Doe!
You have 3 upcoming events
✓ Data saved to meetup_data.json
```

## Files Created

- `meetup_data.json` - Your profile and events data