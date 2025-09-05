from celery import shared_task
import logging
from django.core.files.storage import default_storage
from .models import Upload, Photo, Question, Answer
from .ocr import OCRProcessor
from .ai import LLMChain

logger = logging.getLogger(__name__)

@shared_task
def process_upload(upload_id):
    """
    Main task to process an upload batch.
    Processes each photo sequentially.
    """
    try:
        upload = Upload.objects.get(id=upload_id)
        upload.status = 'processing'
        upload.save()
        
        # Get the first photo in the sequence
        first_photo = upload.photos.order_by('order').first()
        
        if first_photo:
            # Start the processing chain
            process_single_photo.delay(first_photo.id)
            return f"Started processing for upload {upload_id}"
        else:
            # No photos to process, mark as done
            upload.status = 'done'
            upload.save()
            return f"No photos found for upload {upload_id}"
        
    except Upload.DoesNotExist:
        logger.error(f"Upload {upload_id} not found")
        return f"Upload {upload_id} not found"
    except Exception as e:
        logger.error(f"Error starting upload {upload_id}: {str(e)}")
        if 'upload' in locals() and upload:
            upload.status = 'error'
            upload.save()
        return f"Error: {str(e)}"

@shared_task
def process_single_photo(photo_id):
    """
    Process a single photo: OCR, LLM querying, and then trigger the next photo.
    """
    try:
        photo = Photo.objects.get(id=photo_id)
        upload = photo.upload
        
        # Create or get Question object
        question, created = Question.objects.get_or_create(photo=photo)
        
        # Step 1: OCR Extraction
        logger.info(f"Extracting text from photo {photo.id}")
        question.status = 'extracting'
        question.save()
        
        ocr = OCRProcessor()
        try:
            extracted_text = ocr.extract_text(photo.image.path)
            question.extracted_text = extracted_text
            question.status = 'solving'
            question.save()
            logger.info(f"Extracted text: {extracted_text[:100]}...")
        except Exception as e:
            logger.error(f"OCR failed for photo {photo.id}: {str(e)}")
            question.status = 'error'
            question.error_message = f"OCR extraction failed: {str(e)}"
            question.save()
            # Still trigger the next photo even if OCR fails
            trigger_next_photo(photo)
            return f"OCR failed: {str(e)}"
        
        # Step 2: Query LLM Chain
        logger.info(f"Querying LLMs for question {question.id}")
        
        llm_chain = LLMChain()
        result = llm_chain.query_with_fallback(extracted_text)
        
        if result['success']:
            Answer.objects.create(
                question=question,
                provider=result['provider'],
                model=result['model'],
                content=result['answer'],
                status='success',
                response_time=result.get('response_time'),
                tokens_used=result.get('tokens_used')
            )
            question.status = 'answered'
            logger.info(f"Successfully answered question {question.id} using {result['provider']}")
        else:
            question.status = 'error'
            question.error_message = result['error']
            logger.error(f"All LLM providers failed for question {question.id}")
        
        question.save()
        
        # Step 3: Trigger the next photo in the sequence
        trigger_next_photo(photo)
        
        return f"Processed photo {photo.id}"
        
    except Photo.DoesNotExist:
        logger.error(f"Photo {photo_id} not found")
        return f"Photo {photo_id} not found"
    except Exception as e:
        logger.error(f"Error processing photo {photo_id}: {str(e)}")
        try:
            question = Question.objects.get(photo_id=photo_id)
            question.status = 'error'
            question.error_message = f"Unhandled exception: {str(e)}"
            question.save()
            # Still try to trigger the next photo
            trigger_next_photo(question.photo)
        except (Question.DoesNotExist, Photo.DoesNotExist):
            pass
        return f"Error: {str(e)}"

def trigger_next_photo(current_photo):
    """
    Finds the next photo in the upload sequence and triggers its processing.
    If no more photos are left, it finalizes the upload status.
    """
    upload = current_photo.upload
    
    # Update progress after each photo is processed
    update_upload_progress(upload.id)
    
    # Find the next photo
    next_photo = upload.photos.filter(order__gt=current_photo.order).order_by('order').first()
    
    if next_photo:
        logger.info(f"Queueing next photo {next_photo.id} for upload {upload.id}")
        process_single_photo.delay(next_photo.id)
    else:
        # This was the last photo, finalize the upload
        logger.info(f"All photos processed for upload {upload.id}")
        # The update_upload_progress should handle setting the status to 'done'
        # but we can call it one last time to be sure.
        update_upload_progress(upload.id)

def update_upload_progress(upload_id):
    """
    Update the progress of an upload batch. If all photos are processed,
    mark the upload as 'done'.
    """
    try:
        upload = Upload.objects.get(id=upload_id)
        
        # Ensure we have the latest count from the database
        total_photos = upload.photos.count()
        processed_photos = upload.photos.filter(
            question__status__in=['answered', 'error']
        ).count()
        
        upload.processed_photos = processed_photos
        
        # Check if all photos are processed
        if upload.processed_photos >= total_photos:
            upload.status = 'done'
            logger.info(f"Upload {upload.id} completed.")
        
        upload.save()
        
        logger.info(f"Upload {upload.id} progress: {processed_photos}/{total_photos}")
    except Upload.DoesNotExist:
        logger.error(f"Cannot update progress, Upload {upload_id} not found.")


@shared_task
def cleanup_old_uploads():
    """
    Periodic task to clean up old uploads and their files.
    Run this daily via Celery Beat.
    """
    from datetime import timedelta
    from django.utils import timezone
    
    cutoff_date = timezone.now() - timedelta(days=7)
    old_uploads = Upload.objects.filter(created_at__lt=cutoff_date)
    count = old_uploads.count()
    
    for upload in old_uploads:
        # Delete associated files
        for photo in upload.photos.all():
            if photo.image:
                default_storage.delete(photo.image.name)
        
        upload.delete()
    
    logger.info(f"Cleaned up {count} old uploads")
    return f"Cleaned up {count} old uploads"