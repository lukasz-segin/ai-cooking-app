from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from django.conf import settings
import logging
from pathlib import Path
import mimetypes
from io import BytesIO
from typing import Dict, Any
import asyncio

logger = logging.getLogger(__name__)

class GoogleDriveService:
    def __init__(self):
        self.credentials = self._get_credentials()
        self.service = build('drive', 'v3', credentials=self.credentials)
        
        self.mime_types = {
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'pdf': 'application/pdf',
            'googleDoc': 'application/vnd.google-apps.document',
            'googleSheet': 'application/vnd.google-apps.spreadsheet',
        }

    def _get_credentials(self):
        """Get Google Drive credentials using service account file"""
        try:
            # Path to your service account key file
            service_account_file = Path(settings.GOOGLE_SERVICE_ACCOUNT_FILE)

            if not service_account_file.exists():
                logger.warning(f"Service account file not found at {service_account_file}")
                return None

            credentials = service_account.Credentials.from_service_account_file(
                str(service_account_file),
                scopes=["https://www.googleapis.com/auth/drive.file"],
            )
            return credentials

        except Exception as e:
            logger.error(f"Failed to initialize Google credentials: {e}")
            return None

    def upload_file(self, file_path: Path, mime_type: str = None) -> Dict[str, Any]:
        """Upload a file to Google Drive"""
        try:
            if mime_type is None:
                mime_type = mimetypes.guess_type(str(file_path))[0]
                
            file_metadata = {'name': file_path.name}
            with open(file_path, 'rb') as f:
                media = MediaIoBaseUpload(BytesIO(f.read()), mime_type)
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id,name,webViewLink'
                ).execute()
            return file
        except Exception as e:
            logger.error(f"Error uploading file to Google Drive: {e}")
            raise 

    def upload_and_convert(self, file_path: Path) -> Dict[str, Any]:
        """Upload file to Google Drive and convert to Google Doc/Sheet if possible."""
        try:
            mime_type = mimetypes.guess_type(str(file_path))[0]
            
            # Upload file
            file_metadata = {'name': file_path.name}
            with open(file_path, 'rb') as f:
                media = MediaIoBaseUpload(BytesIO(f.read()), mime_type)
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id,name,webViewLink'
                ).execute()
            
            # Convert to Google format if it's a document/spreadsheet
            if mime_type in ['application/pdf', 'application/msword', 
                            'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                # Copy to Google Doc format
                copied_file = self.service.files().copy(
                    fileId=file['id'],
                    body={'mimeType': 'application/vnd.google-apps.document'}
                ).execute()
                
                # Export as plain text
                text_content = self.service.files().export(
                    fileId=copied_file['id'],
                    mimeType='text/plain'
                ).execute()
                
                # Clean up - delete the Google Doc copy (optional)
                self.service.files().delete(fileId=copied_file['id']).execute()
                
                return {
                    "id": file['id'],
                    "webViewLink": file['webViewLink'],
                    "text": text_content.decode('utf-8') if isinstance(text_content, bytes) else text_content
                }
            
            return {
                "id": file['id'],
                "webViewLink": file['webViewLink']
            }
        
        except Exception as e:
            logger.error(f"Error in upload_and_convert: {e}")
            raise

    def download_file(self, file_id: str) -> bytes:
        """Download a file from Google Drive by ID"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_content = request.execute()
            return file_content
        except Exception as e:
            logger.error(f"Error downloading file from Google Drive: {e}")
            raise

    def process_pdf_with_drive(self, file_path: Path) -> str:
        """Process a PDF file using Google Drive for better text extraction"""
        try:
            result = self.upload_and_convert(file_path)
            
            # Delete the file from Drive after processing
            self.service.files().delete(fileId=result['id']).execute()
            
            return result.get('text', '')
        except Exception as e:
            logger.error(f"Error processing PDF with Google Drive: {e}")
            raise