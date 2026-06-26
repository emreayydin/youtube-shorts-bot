"""Uploads a video to YouTube as a Short using the YouTube Data API v3."""
import os
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "youtube_token.json"
CREDENTIALS_FILE = "client_secrets.json"


def get_youtube_service():
    """Authenticates and returns a YouTube API service object."""
    creds = None

    # In GitHub Actions, use service account token from env
    token_json = os.environ.get("YOUTUBE_TOKEN_JSON")
    if token_json:
        token_data = json.loads(token_json)
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=SCOPES,
        )

    # Local development: use token file
    elif Path(TOKEN_FILE).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        if Path(TOKEN_FILE).exists():
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())

    # First-time local auth flow
    if not creds or not creds.valid:
        if not Path(CREDENTIALS_FILE).exists():
            raise FileNotFoundError(
                f"'{CREDENTIALS_FILE}' nicht gefunden. "
                "Lade deine OAuth2-Credentials von der Google Cloud Console herunter."
            )
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print(f"Token gespeichert: {TOKEN_FILE}")
        print("\nFüge diesen JSON-Inhalt als GitHub Secret 'YOUTUBE_TOKEN_JSON' hinzu:")
        print(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_short(
    video_path: str,
    title: str,
    description: str,
    tags: list[str],
    category_id: str = "27",  # 27 = Education
    privacy: str = "public",  # "public", "private", or "unlisted"
    is_short: bool = True,    # False = normal long-form video (no #Shorts)
) -> str:
    """
    Uploads a video to YouTube. With is_short=True the description carries the
    #Shorts tag so YouTube classifies it as a Short; with is_short=False it is
    uploaded as a normal long-form video.
    Returns the video ID.
    """
    youtube = get_youtube_service()

    if is_short:
        full_description = f"{description}\n\n#Shorts #Fakten #Trivia #Wissen #Lernen"
    else:
        full_description = f"{description}\n\n#Fakten #Trivia #Wissen #Lernen #Doku"
    if tags:
        full_description += "\n" + " ".join(f"#{t}" for t in tags[:5])

    body = {
        "snippet": {
            "title": title,
            "description": full_description,
            "tags": tags + (["Shorts"] if is_short else []) + ["Fakten", "Trivia", "Wissen"],
            "categoryId": category_id,
            "defaultLanguage": "de",
            "defaultAudioLanguage": "de",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload: {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"Video hochgeladen: https://youtube.com/watch?v={video_id}")
    return video_id


def set_thumbnail(video_id: str, thumbnail_path: str) -> bool:
    """Sets a custom thumbnail for a video. Returns True on success."""
    try:
        youtube = get_youtube_service()
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path, mimetype="image/png"),
        ).execute()
        print(f"Thumbnail gesetzt für {video_id}")
        return True
    except Exception as e:
        # Needs a verified channel; if it fails, the video keeps its auto-thumbnail
        print(f"Thumbnail konnte nicht gesetzt werden ({e}). Video bleibt bei Auto-Thumbnail.")
        return False


if __name__ == "__main__":
    # Run authentication flow locally
    print("Starte YouTube-Authentifizierung...")
    get_youtube_service()
    print("Authentifizierung erfolgreich!")
