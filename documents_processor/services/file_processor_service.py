from django.conf import settings
from pathlib import Path
import logging
from typing import List
import PyPDF2

from .openai_service import OpenAIService
from .vector_service import VectorService
from .google_drive_service import GoogleDriveService
from .text_splitter_service import TextSplitterService
from ..models import StoredDocument

logger = logging.getLogger(__name__)

class FileProcessorService:
    def __init__(self):
        self.openai_service = OpenAIService()
        self.vector_service = VectorService(self.openai_service)
        self.text_splitter = TextSplitterService()
        self.google_drive_service = GoogleDriveService()

    def process_document(self, document_id: str, use_google_drive: bool = False):
        try:
            document = StoredDocument.objects.get(id=document_id)
            logger.info(f"Starting to process document {document_id}")
            document.status = 'processing'
            document.save()

            if use_google_drive:
                # Process with Google Drive
                logger.info(f"Using Google Drive for enhanced text extraction")
                file_path = Path(document.file_path)
                result = self.google_drive_service.process_pdf_with_drive(file_path)
                
                # Process the entire text from Google Drive
                chunks = self.text_splitter.split_text(result)
                logger.info(f"Document split into {len(chunks)} chunks")
                
                chunk_index = 0
                successful_chunks = 0
                
                for chunk_num, chunk in enumerate(chunks):
                    try:
                        self.vector_service.store_chunk(
                            document=document,
                            chunk_text=chunk['text'],
                            chunk_index=chunk_index
                        )
                        chunk_index += 1
                        successful_chunks += 1
                    except Exception as e:
                        logger.error(f"Error processing chunk {chunk_num}: {e}")
                        continue
            else:
                # Process with PyPDF2 (original method)
                with open(document.file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    logger.info(f"PDF loaded with {len(pdf_reader.pages)} pages")
                    
                    chunk_index = 0
                    successful_chunks = 0
                    
                    for page_num, page in enumerate(pdf_reader.pages):
                        logger.info(f"Processing page {page_num + 1}/{len(pdf_reader.pages)}")
                        try:
                            text = page.extract_text()
                            chunks = self.text_splitter.split_text(text)
                            logger.info(f"Page {page_num + 1} split into {len(chunks)} chunks")
                            
                            for chunk_num, chunk in enumerate(chunks):
                                try:
                                    self.vector_service.store_chunk(
                                        document=document,
                                        chunk_text=chunk['text'],
                                        chunk_index=chunk_index
                                    )
                                    chunk_index += 1
                                    successful_chunks += 1
                                    logger.info(f"Successfully stored chunk {chunk_num + 1}/{len(chunks)} from page {page_num + 1}")
                                except Exception as e:
                                    logger.error(f"Error processing chunk {chunk_num + 1} in page {page_num + 1}: {e}")
                                    continue
                        
                        except Exception as e:
                            logger.error(f"Error processing page {page_num + 1}: {e}")
                            continue

            final_status = 'processed' if successful_chunks > 0 else 'error'
            logger.info(f"Document processing completed. Status: {final_status}, Successful chunks: {successful_chunks}")
            document.status = final_status
            document.save()
        
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}")
            document.status = 'error'
            document.save()
            raise 

    def process_document_with_google_drive_in_batches(self, document_id: str, batch_size: int = 20):
        """Process a large document by splitting it into smaller batches for Google Drive"""
        try:
            document = StoredDocument.objects.get(id=document_id)
            logger.info(f"Starting to process document {document_id} with Google Drive in batches")
            document.status = 'processing'
            document.save()
            
            file_path = Path(document.file_path)
            
            # Split PDF into smaller PDFs (using PyPDF2 to split)
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                logger.info(f"PDF has {total_pages} pages, processing in batches")
                
                chunk_index = 0
                successful_chunks = 0
                
                # Process PDF in batches
                for batch_start in range(0, total_pages, batch_size):
                    batch_end = min(batch_start + batch_size, total_pages)
                    logger.info(f"Processing batch of pages {batch_start+1}-{batch_end}")
                    
                    # Create temporary PDF with this batch of pages
                    pdf_writer = PyPDF2.PdfWriter()
                    for page_num in range(batch_start, batch_end):
                        pdf_writer.add_page(pdf_reader.pages[page_num])
                    
                    # Save temporary batch PDF
                    temp_pdf_path = file_path.with_name(f"{file_path.stem}_batch_{batch_start}.pdf")
                    with open(temp_pdf_path, 'wb') as temp_file:
                        pdf_writer.write(temp_file)
                    
                    # Process this batch with Google Drive
                    try:
                        batch_text = self.google_drive_service.process_pdf_with_drive(temp_pdf_path)
                        batch_chunks = self.text_splitter.split_text(batch_text)
                        
                        for chunk_num, chunk in enumerate(batch_chunks):
                            try:
                                self.vector_service.store_chunk(
                                    document=document,
                                    chunk_text=chunk['text'],
                                    chunk_index=chunk_index
                                )
                                chunk_index += 1
                                successful_chunks += 1
                            except Exception as e:
                                logger.error(f"Error processing chunk {chunk_num} in batch {batch_start}: {e}")
                                continue
                        
                        # Clean up temporary file
                        temp_pdf_path.unlink()
                        
                    except Exception as e:
                        logger.error(f"Error processing batch {batch_start}-{batch_end}: {e}")
                        continue
                
                final_status = 'processed' if successful_chunks > 0 else 'error'
                logger.info(f"Document processing completed. Status: {final_status}, Successful chunks: {successful_chunks}")
                document.status = final_status
                document.save()
        
        except Exception as e:
            logger.error(f"Error processing document {document_id} with batched Google Drive: {e}")
            document.status = 'error'
            document.save()
            raise 