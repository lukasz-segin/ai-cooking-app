from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from .models import StoredDocument
from .serializers import StoredDocumentSerializer
from .services.file_processor_service import FileProcessorService
from pathlib import Path
from django.conf import settings
from .services.google_drive_service import GoogleDriveService

# Create your views here.

class DocumentProcessorViewSet(viewsets.ModelViewSet):
    queryset = StoredDocument.objects.all()
    serializer_class = StoredDocumentSerializer
    
    @action(detail=False, methods=['post'])
    def process_document(self, request):
        file_name = request.data.get('file_name')
        use_google_drive = request.data.get('use_google_drive', False)
        
        if not file_name:
            return Response(
                {"error": "No file name provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Assuming documents are stored in a specific directory
        file_path = Path(settings.DOCUMENTS_DIR) / file_name
        
        if not file_path.exists():
            return Response(
                {"error": f"File {file_name} not found in documents directory"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create StoredDocument with pending status
        document = StoredDocument.objects.create(
            file_path=str(file_path),
            title=file_name,
            status='pending'
        )

        # Initialize processor and start processing
        processor = FileProcessorService()
        try:
            processor.process_document(str(document.id), use_google_drive=use_google_drive)
            return Response({
                "message": "Document processing started",
                "document_id": document.id,
                "using_google_drive": use_google_drive
            })
        except Exception as e:
            document.status = 'error'
            document.save()
            return Response({
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def process_drive_document(self, request):
        drive_file_id = request.data.get('drive_file_id')
        if not drive_file_id:
            return Response(
                {"error": "No drive file ID provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Initialize Google Drive service
        drive_service = GoogleDriveService()
        
        try:
            # Download file from Google Drive
            file_content = drive_service.download_file(drive_file_id)
            
            # Save to temporary file
            temp_file_path = Path(settings.DOCUMENTS_DIR) / f"drive_{drive_file_id}.pdf"
            with open(temp_file_path, 'wb') as f:
                f.write(file_content)
            
            # Create StoredDocument with pending status
            document = StoredDocument.objects.create(
                file_path=str(temp_file_path),
                title=f"Google Drive Document {drive_file_id}",
                status='pending'
            )
            
            # Initialize processor and start processing
            processor = FileProcessorService()
            processor.process_document(str(document.id))
            
            return Response({
                "message": "Document processing started",
                "document_id": document.id
            })
        except Exception as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_document_status(request, document_id):
    try:
        document = StoredDocument.objects.get(id=document_id)
        return Response({
            'id': document.id,
            'status': document.status,
            'title': document.title,
            'created_at': document.created_at
        })
    except StoredDocument.DoesNotExist:
        return Response({'error': 'Document not found'}, status=404)
