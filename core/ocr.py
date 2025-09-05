import pytesseract
from PIL import Image
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class OCRProcessor:
    def __init__(self):
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    
    def extract_text(self, image_path):
        """
        Extract text from an image using Tesseract OCR.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Extracted text string
        """
        try:
            # Open and preprocess image for better results
            image = self.preprocess_image(image_path)
            
            # Extract text with custom config for better accuracy
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(image, config=custom_config)
            
            # Clean up the text
            text = text.strip()
            
            if not text:
                logger.warning(f"No text extracted from image: {image_path}")
                return "No text could be extracted from this image."
            
            logger.info(f"Successfully extracted {len(text)} characters from {image_path}")
            return text
            
        except Exception as e:
            logger.error(f"OCR extraction failed for {image_path}: {str(e)}")
            raise Exception(f"OCR extraction failed: {str(e)}")
    
    def preprocess_image(self, image_path):
        """
        Preprocess image for better OCR accuracy.
        This can be enhanced with more advanced techniques like deskewing or noise removal.
        """
        try:
            from PIL import ImageEnhance, ImageFilter
            
            image = Image.open(image_path)
            
            # Convert to grayscale
            image = image.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            return image
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {str(e)}")
            # Return original image if preprocessing fails
            return Image.open(image_path)