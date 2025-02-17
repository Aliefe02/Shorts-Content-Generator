import os
import google_auth_httplib2
import googleapiclient.discovery
import googleapiclient.errors
import googleapiclient.http
import google_auth_oauthlib

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def authenticate_youtube():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    # Load client secrets file, put the path of your file
    client_secrets_file = "/home/ali/Desktop/MoneyPrinter/client_secret_yt.json"

    
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, SCOPES)
    credentials = flow.run_local_server()

    youtube = googleapiclient.discovery.build(
        "youtube", "v3", credentials=credentials)

    return youtube

def upload_video(youtube, title, categoryId, description, tags, file_location, privacy_status):

    if "#Shorts" not in title:
        title += " #Shorts"
    if "#Shorts" not in description:
        description += " #Shorts"
    
    request_body = {
        "snippet": {
            "categoryId": categoryId,
            "title": title,
            "description": description,
            "tags": tags
        },
        "status":{
            "privacyStatus": privacy_status
        }
    }

    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=googleapiclient.http.MediaFileUpload(file_location, chunksize=-1, resumable=True)
    )

    response = None

    while response is None:
        status, response = request.next_chunk()

        if status:
            print(f"Upload {int(status.progress()*100)}%")
        
        print(f"Video uploaded with ID: {response['id']}")
    
    return response['id']

    