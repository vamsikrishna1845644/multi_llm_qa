import time
import logging
from typing import Dict, Any
from django.conf import settings
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

class LLMProvider:
    """Base class for LLM providers"""
    
    def __init__(self, name: str, api_key: str):
        self.name = name
        self.api_key = api_key
        self.model = None
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        Query the LLM with a question.
        
        Returns:
            Dict with keys: success, answer, model, tokens_used, error
        """
        raise NotImplementedError

class GeminiProvider(LLMProvider):
    def __init__(self):
        super().__init__('gemini', settings.GOOGLE_API_KEY)
        self.model = 'gemini-pro'
    
    def query(self, question: str) -> Dict[str, Any]:
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            
            prompt = f"Please solve this question and provide a clear, step-by-step solution:\n\n{question}"
            
            start_time = time.time()
            response = model.generate_content(prompt)
            response_time = time.time() - start_time
            
            return {
                'success': True,
                'provider': self.name,
                'answer': response.text,
                'model': self.model,
                'response_time': response_time,
                'tokens_used': None,  # Gemini API v1 doesn't easily provide token count
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Gemini query failed: {str(e)}")
            return {'success': False, 'provider': self.name, 'answer': None, 'model': self.model, 'response_time': None, 'tokens_used': None, 'error': str(e)}

class OpenAIProvider(LLMProvider):
    def __init__(self):
        super().__init__('openai', settings.OPENAI_API_KEY)
        self.model = 'gpt-3.5-turbo'
    
    def query(self, question: str) -> Dict[str, Any]:
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.api_key)
            
            messages = [
                {"role": "system", "content": "You are a helpful assistant that solves questions clearly and accurately."},
                {"role": "user", "content": f"Please solve this question and provide a clear, step-by-step solution:\n\n{question}"}
            ]
            
            start_time = time.time()
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1500
            )
            response_time = time.time() - start_time
            
            return {
                'success': True,
                'provider': self.name,
                'answer': response.choices[0].message.content,
                'model': self.model,
                'response_time': response_time,
                'tokens_used': response.usage.total_tokens if response.usage else None,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"OpenAI query failed: {str(e)}")
            return {'success': False, 'provider': self.name, 'answer': None, 'model': self.model, 'response_time': None, 'tokens_used': None, 'error': str(e)}

class AnthropicProvider(LLMProvider):
    def __init__(self):
        super().__init__('anthropic', settings.ANTHROPIC_API_KEY)
        self.model = 'claude-3-sonnet-20240229'
    
    def query(self, question: str) -> Dict[str, Any]:
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            prompt = f"Please solve this question and provide a clear, step-by-step solution:\n\n{question}"
            
            start_time = time.time()
            response = client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            response_time = time.time() - start_time
            
            return {
                'success': True,
                'provider': self.name,
                'answer': response.content[0].text if response.content else "",
                'model': self.model,
                'response_time': response_time,
                'tokens_used': response.usage.input_tokens + response.usage.output_tokens if response.usage else None,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Anthropic query failed: {str(e)}")
            return {'success': False, 'provider': self.name, 'answer': None, 'model': self.model, 'response_time': None, 'tokens_used': None, 'error': str(e)}

class GroqProvider(LLMProvider):
    def __init__(self):
        super().__init__('groq', settings.GROQ_API_KEY)
        self.model = 'mixtral-8x7b-32768'
    
    def query(self, question: str) -> Dict[str, Any]:
        try:
            from groq import Groq
            
            client = Groq(api_key=self.api_key)
            
            messages = [
                {"role": "system", "content": "You are a helpful assistant that solves questions clearly and accurately."},
                {"role": "user", "content": f"Please solve this question and provide a clear, step-by-step solution:\n\n{question}"}
            ]
            
            start_time = time.time()
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1500
            )
            response_time = time.time() - start_time
            
            return {
                'success': True,
                'provider': self.name,
                'answer': response.choices[0].message.content,
                'model': self.model,
                'response_time': response_time,
                'tokens_used': response.usage.total_tokens if hasattr(response, 'usage') else None,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Groq query failed: {str(e)}")
            return {'success': False, 'provider': self.name, 'answer': None, 'model': self.model, 'response_time': None, 'tokens_used': None, 'error': str(e)}

class LLMChain:
    """
    Manages querying LLM providers in parallel and returning the first successful response.
    """
    def __init__(self):
        self.providers = []
        
        # Initialize providers if their API key exists
        if settings.GOOGLE_API_KEY:
            self.providers.append(GeminiProvider())
        if settings.OPENAI_API_KEY:
            self.providers.append(OpenAIProvider())
        if settings.ANTHROPIC_API_KEY:
            self.providers.append(AnthropicProvider())
        if settings.GROQ_API_KEY:
            self.providers.append(GroqProvider())
        
        if not self.providers:
            logger.warning("No LLM API keys configured!")
    
    def query_with_fallback(self, question: str) -> Dict[str, Any]:
        """
        Query all LLM providers in parallel and return the first successful response.
        """
        if not self.providers:
            return {'success': False, 'provider': None, 'answer': None, 'error': 'No LLM providers configured'}
        
        errors = {}
        
        with ThreadPoolExecutor(max_workers=len(self.providers)) as executor:
            # Submit all providers to the executor
            future_to_provider = {executor.submit(p.query, question): p for p in self.providers}
            
            for future in as_completed(future_to_provider):
                provider = future_to_provider[future]
                try:
                    result = future.result()
                    if result['success']:
                        logger.info(f"Successfully got answer from {provider.name}")
                        # Cancel remaining futures
                        for f in future_to_provider:
                            f.cancel()
                        return result
                    else:
                        errors[provider.name] = result['error']
                        logger.warning(f"{provider.name} failed: {result['error']}")
                except Exception as e:
                    errors[provider.name] = str(e)
                    logger.error(f"Exception from {provider.name}: {str(e)}")
        
        # All providers failed
        error_summary = ' | '.join([f"{p}: {e}" for p, e in errors.items()])
        return {'success': False, 'provider': None, 'answer': None, 'error': error_summary}