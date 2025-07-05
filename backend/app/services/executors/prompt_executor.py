"""
Prompt Function Executor for AI-powered prompt processing
Supports OpenAI GPT models with template processing and response formatting
"""
import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from jinja2 import Template

from openai import AsyncOpenAI

from ...core.config import settings
from ...models.function import Function


class PromptExecutor:
    """
    AI-powered prompt function executor with OpenAI integration
    """
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
    async def execute(self, function: Function, parameters: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a prompt function with AI processing
        
        Args:
            function: Function object with prompt configuration
            parameters: Function parameters from user input
            context: Execution context
            
        Returns:
            Dict containing AI response and metadata
        """
        if not function.prompt_template:
            raise ValueError("Prompt template is required for prompt functions")
        
        start_time = time.time()
        
        try:
            # Build the prompt from template
            rendered_prompt = self._render_prompt_template(
                function.prompt_template, 
                parameters, 
                context or {}
            )
            
            # Get model configuration
            model_config = self._get_model_config(function)
            
            # Execute AI request
            response = await self._execute_ai_request(rendered_prompt, model_config)
            
            # Process and format response
            formatted_response = self._format_response(response, model_config)
            
            execution_time = time.time() - start_time
            
            return {
                "success": True,
                "result": formatted_response,
                "metadata": {
                    "execution_time": execution_time,
                    "model": model_config.get("model", "gpt-4"),
                    "prompt_length": len(rendered_prompt),
                    "response_length": len(str(formatted_response)),
                    "tokens_used": response.get("usage", {}).get("total_tokens", 0),
                    "temperature": model_config.get("temperature", 0.7)
                }
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "execution_time": execution_time,
                    "model": function.extra_data.get("model", "gpt-4") if function.extra_data else "gpt-4"
                }
            }
    
    def _render_prompt_template(self, template_str: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Render prompt template with parameters and context"""
        
        try:
            # Create Jinja2 template
            template = Template(template_str)
            
            # Prepare template variables
            template_vars = {}
            template_vars.update(parameters)
            template_vars.update(context)
            
            # Add system variables
            template_vars.update({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'date': time.strftime('%Y-%m-%d'),
                'time': time.strftime('%H:%M:%S')
            })
            
            # Render template
            rendered = template.render(**template_vars)
            
            return rendered.strip()
            
        except Exception as e:
            raise ValueError(f"Error rendering prompt template: {e}")
    
    def _get_model_config(self, function: Function) -> Dict[str, Any]:
        """Extract model configuration from function"""
        
        # Default configuration
        config = {
            "model": settings.OPENAI_MODEL,
            "temperature": settings.OPENAI_TEMPERATURE,
            "max_tokens": settings.OPENAI_MAX_TOKENS,
            "response_format": "text"
        }
        
        # Override with function-specific config from extra_data
        if function.extra_data:
            model_config = function.extra_data.get("model_config", {})
            config.update(model_config)
        
        # Validate model configuration
        config["temperature"] = max(0.0, min(2.0, config.get("temperature", 0.7)))
        config["max_tokens"] = max(1, min(4000, config.get("max_tokens", 1000)))
        
        return config
    
    async def _execute_ai_request(self, prompt: str, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute AI request with OpenAI"""
        
        try:
            # Prepare messages
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            # Add system prompt if configured
            system_prompt = model_config.get("system_prompt")
            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})
            
            # Prepare request parameters
            request_params = {
                "model": model_config["model"],
                "messages": messages,
                "temperature": model_config["temperature"],
                "max_tokens": model_config["max_tokens"]
            }
            
            # Handle response format
            response_format = model_config.get("response_format", "text")
            if response_format == "json":
                request_params["response_format"] = {"type": "json_object"}
            
            # Add other parameters if specified
            for param in ["top_p", "frequency_penalty", "presence_penalty"]:
                if param in model_config:
                    request_params[param] = model_config[param]
            
            # Execute request
            response = await self.openai_client.chat.completions.create(**request_params)
            
            # Extract response data
            choice = response.choices[0]
            
            return {
                "content": choice.message.content,
                "finish_reason": choice.finish_reason,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "model": response.model
            }
            
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}")
    
    def _format_response(self, response: Dict[str, Any], model_config: Dict[str, Any]) -> Any:
        """Format AI response based on configuration"""
        
        content = response.get("content", "")
        response_format = model_config.get("response_format", "text")
        
        if response_format == "json":
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # If JSON parsing fails, return as text with warning
                return {
                    "content": content,
                    "warning": "Response was not valid JSON despite json format request"
                }
        
        elif response_format == "text":
            return content
        
        else:
            # Auto-detect format
            try:
                # Try to parse as JSON first
                return json.loads(content)
            except json.JSONDecodeError:
                # Return as text if not JSON
                return content
    
    async def close(self):
        """Close OpenAI client"""
        if self.openai_client:
            await self.openai_client.close()


# Example prompt configurations
EXAMPLE_PROMPT_CONFIGS = {
    "code_reviewer": {
        "prompt_template": """
You are an expert code reviewer. Please review the following code and provide feedback.

Code to review:
```{{ language | default('python') }}
{{ code }}
```

Please provide:
1. Overall assessment
2. Specific issues found
3. Suggestions for improvement
4. Security considerations

Review:""",
        "model_config": {
            "model": "gpt-4",
            "temperature": 0.3,
            "max_tokens": 1500,
            "response_format": "text"
        }
    },
    
    "data_analyzer": {
        "prompt_template": """
You are a data analyst. Analyze the following data and provide insights.

Data:
{{ data }}

Analysis Context:
- Purpose: {{ purpose | default('General analysis') }}
- Focus Areas: {{ focus_areas | default('Trends, patterns, anomalies') }}

Please provide your analysis in JSON format with the following structure:
{
    "summary": "Brief overview of the data",
    "key_insights": ["insight1", "insight2", "insight3"],
    "trends": ["trend1", "trend2"],
    "recommendations": ["rec1", "rec2"],
    "confidence_level": "high|medium|low"
}

Analysis:""",
        "model_config": {
            "model": "gpt-4",
            "temperature": 0.4,
            "max_tokens": 2000,
            "response_format": "json"
        }
    },
    
    "meeting_summarizer": {
        "prompt_template": """
You are an expert meeting assistant. Please summarize the following meeting transcript.

Meeting Details:
- Date: {{ date }}
- Participants: {{ participants | join(', ') }}
- Duration: {{ duration | default('Unknown') }}

Transcript:
{{ transcript }}

Please provide a comprehensive summary including:
1. Key discussion points
2. Decisions made
3. Action items with owners
4. Next steps

Summary:""",
        "model_config": {
            "model": "gpt-4",
            "temperature": 0.2,
            "max_tokens": 1000,
            "response_format": "text",
            "system_prompt": "You are a professional meeting assistant focused on creating clear, actionable summaries."
        }
    },
    
    "creative_writer": {
        "prompt_template": """
You are a creative writing assistant. Please help with the following writing task.

Writing Request:
- Type: {{ writing_type | default('story') }}
- Genre: {{ genre | default('fiction') }}
- Tone: {{ tone | default('engaging') }}
- Length: {{ length | default('short') }}

Prompt: {{ prompt }}

Additional Context:
{{ context | default('') }}

Please create compelling content that matches the specified parameters.

Content:""",
        "model_config": {
            "model": "gpt-4",
            "temperature": 0.8,
            "max_tokens": 2000,
            "response_format": "text"
        }
    }
}