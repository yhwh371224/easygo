import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail"]


def main():
  """Shows basic usage of the Gmail API.
  Lists the user's Gmail labels.
  """
  creds = None
  secure_directory = 'secure_gmail/'
  token_file_path = os.path.join(secure_directory, 'token.json')   
  if os.path.exists(token_file_path):
      creds = Credentials.from_authorized_user_file(token_file_path, SCOPES)       
  if not creds or not creds.valid:
      if creds and creds.expired and creds.refresh_token:
          creds.refresh(Request())
      else:
          credentials_file_path = os.path.join(secure_directory, 'credentials.json')
          flow = InstalledAppFlow.from_client_secrets_file(credentials_file_path, SCOPES)
          creds = flow.run_local_server(port=0)    
      with open('token.json', 'w') as token:
          token.write(creds.to_json())  
          
  try:
    # Call the Gmail API
    service = build("gmail", "v1", credentials=creds)
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])

    if not labels:
      print("No labels found.")
      return
    print("Labels:")

    for label in labels:
      if label['name'] == 'Re-reminder':
        print(f"Label ID for 'Re-reminder': {label['id']}")

  except HttpError as error:
    # TODO(developer) - Handle errors from gmail API.
    print(f"An error occurred: {error}")


if __name__ == "__main__":
  main()