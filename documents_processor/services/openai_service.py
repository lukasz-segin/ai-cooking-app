from openai import OpenAI
import logging
from ai_cooking_project import settings

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def create_embedding(self, text: str) -> list[float]:
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            raise 

    def create_completion(self, request):
        """
        Synchronous wrapper for completion API
        
        Args:
            request: ChatRequest object with messages and model information
            
        Returns:
            ChatResponse object with generated content
        """
        try:
            # Extract messages from request
            messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
            
            # Determine if JSON mode should be used
            response_format = {"type": "json_object"} if request.json_mode else None
            
            # Call the OpenAI API synchronously
            response = self.client.chat.completions.create(
                model=request.model,
                messages=messages,
                response_format=response_format,
                max_tokens=request.max_tokens
            )
            
            # Create a simple response object
            class SimpleResponse:
                def __init__(self, content):
                    self.content = content
            
            # Return a simple response object with the content
            return SimpleResponse(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error in OpenAI completion: {e}")
            raise

    def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        model: str = "dall-e-3",
    ) -> str:
        """
        Generate image using OpenAI's DALL-E model (synchronous version).
        
        Args:
            prompt: Text description of the image to generate
            size: Image size (e.g., "1024x1024")
            quality: Image quality ("standard" or "hd")
            model: DALL-E model version to use
            
        Returns:
            URL of the generated image
        """
        try:
            logger.info(f"Generating image with prompt: '{prompt[:50]}...' using model {model}")
            response = self.client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                quality=quality,
                n=1,
            )
            image_url = response.data[0].url
            logger.info(f"Image generated successfully: {image_url}")
            return image_url
        except Exception as error:
            logger.error(f"Error in OpenAI image generation: {error}")
            raise 