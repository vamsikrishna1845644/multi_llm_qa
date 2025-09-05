from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Upload
from .serializers import UploadSerializer

class UploadViewSet(viewsets.ModelViewSet):
    """
    API endpoint to upload photos, monitor processing, and view results.

    - **POST /api/uploads/**: Creates a new upload job. Submit a list of images
      via multipart/form-data with the key `uploaded_photos`.
    - **GET /api/uploads/**: Lists all previous upload jobs.
    - **GET /api/uploads/{id}/**: Retrieves the detailed status and results for
      a specific upload job.
    """
    queryset = Upload.objects.all().prefetch_related('photos__question__answers')
    serializer_class = UploadSerializer
    # We only need list, create, and retrieve functionality
    http_method_names = ['get', 'post', 'head', 'options']

    def create(self, request, *args, **kwargs):
        """
        Override the create method to return the full serialized object,
        which is more useful for the client after an upload.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Re-serialize the instance to include nested relationships like 'photos'
        instance = serializer.instance
        detail_serializer = self.get_serializer(instance)
        
        headers = self.get_success_headers(detail_serializer.data)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED, headers=headers)