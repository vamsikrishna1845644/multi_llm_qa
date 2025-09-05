from rest_framework import serializers
from .models import Upload, Photo, Question, Answer

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = [
            'id', 'provider', 'model', 'content', 
            'status', 'error_message', 'tokens_used', 
            'response_time', 'created_at'
        ]

class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)
    latest_answer = serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = [
            'id', 'extracted_text', 'status', 
            'error_message', 'answers', 'latest_answer',
            'created_at', 'updated_at'
        ]
    
    def get_latest_answer(self, obj):
        """
        Finds the most recent successful answer for a question.
        """
        successful_answer = obj.answers.filter(status='success').order_by('-created_at').first()
        if successful_answer:
            return AnswerSerializer(successful_answer).data
        return None

class PhotoSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    image_url = serializers.ImageField(source='image', read_only=True)

    class Meta:
        model = Photo
        fields = ['id', 'order', 'filename', 'image_url', 'question', 'uploaded_at']

class UploadSerializer(serializers.ModelSerializer):
    photos = PhotoSerializer(many=True, read_only=True)
    # This write-only field handles the file uploads from the client
    uploaded_photos = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False, use_url=False),
        write_only=True,
        help_text="List of images to upload for processing."
    )
    progress_percentage = serializers.ReadOnlyField()

    class Meta:
        model = Upload
        fields = [
            'id', 'status', 'total_photos', 'processed_photos', 
            'progress_percentage', 'created_at', 'updated_at',
            'photos', 'uploaded_photos'
        ]
        read_only_fields = ['status', 'total_photos', 'processed_photos', 'progress_percentage']

    def create(self, validated_data):
        # Import task locally to avoid circular dependency issues
        from .tasks import process_upload 

        uploaded_photos = validated_data.pop('uploaded_photos')
        
        # Create the main Upload instance
        upload = Upload.objects.create(total_photos=len(uploaded_photos))
        
        # Create Photo instances for each uploaded file in a single DB query
        photo_objects = [
            Photo(
                upload=upload,
                image=image_file,
                filename=image_file.name,
                order=i
            ) for i, image_file in enumerate(uploaded_photos)
        ]
        Photo.objects.bulk_create(photo_objects)
        
        # Trigger the asynchronous Celery task to process the uploaded files
        process_upload.delay(str(upload.id))
        
        return upload