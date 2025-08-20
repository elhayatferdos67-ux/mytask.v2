#!/usr/bin/env python3
"""
ElevenLabs MCP Server for Suna AI
Provides text-to-speech capabilities with credit integration
"""

import asyncio
import aiohttp
import json
import base64
from typing import Any, Sequence
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel
import os
from decimal import Decimal

# Import Suna's billing system
import sys
sys.path.append('/app')
from services.billing import MediaCreditManager
from utils.logger import logger

class ElevenLabsConfig(BaseModel):
    api_key: str
    base_url: str = "https://api.elevenlabs.io/v1"
    default_voice: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
    default_model: str = "eleven_monolingual_v1"

class ElevenLabsMCPServer:
    def __init__(self, config: ElevenLabsConfig):
        self.config = config
        self.server = Server("elevenlabs")
        self.credit_manager = MediaCreditManager()
        self.session = None
        self.setup_tools()
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def setup_tools(self):
        """Setup MCP tools for ElevenLabs integration"""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="text_to_speech",
                    description="Convert text to high-quality speech using ElevenLabs AI",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string", 
                                "description": "Text to convert to speech (max 5000 characters)"
                            },
                            "voice_id": {
                                "type": "string", 
                                "description": "Voice ID to use (optional, defaults to Rachel)",
                                "default": self.config.default_voice
                            },
                            "model": {
                                "type": "string",
                                "description": "Model to use for generation",
                                "enum": ["eleven_monolingual_v1", "eleven_multilingual_v1", "eleven_multilingual_v2"],
                                "default": self.config.default_model
                            },
                            "voice_settings": {
                                "type": "object",
                                "description": "Voice settings for fine-tuning",
                                "properties": {
                                    "stability": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.5},
                                    "similarity_boost": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.5},
                                    "style": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.0}
                                }
                            },
                            "user_id": {
                                "type": "string",
                                "description": "User ID for credit management"
                            }
                        },
                        "required": ["text", "user_id"]
                    }
                ),
                Tool(
                    name="get_voices",
                    description="Get list of available voices from ElevenLabs",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="clone_voice",
                    description="Clone a voice from audio samples",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Name for the cloned voice"},
                            "description": {"type": "string", "description": "Description of the voice"},
                            "audio_files": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Base64 encoded audio files for cloning"
                            },
                            "user_id": {"type": "string", "description": "User ID for credit management"}
                        },
                        "required": ["name", "audio_files", "user_id"]
                    }
                ),
                Tool(
                    name="estimate_cost",
                    description="Estimate cost for text-to-speech generation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "Text to estimate cost for"},
                            "model": {"type": "string", "description": "Model to use", "default": self.config.default_model}
                        },
                        "required": ["text"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> Sequence[TextContent]:
            try:
                if name == "text_to_speech":
                    return await self.text_to_speech(**arguments)
                elif name == "get_voices":
                    return await self.get_voices()
                elif name == "clone_voice":
                    return await self.clone_voice(**arguments)
                elif name == "estimate_cost":
                    return await self.estimate_cost(**arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error(f"Error in ElevenLabs MCP tool {name}: {str(e)}")
                return [TextContent(
                    type="text",
                    text=f"❌ Error: {str(e)}"
                )]
    
    async def text_to_speech(
        self, 
        text: str, 
        user_id: str,
        voice_id: str = None,
        model: str = None,
        voice_settings: dict = None
    ) -> Sequence[TextContent]:
        """Generate speech from text with credit management"""
        
        # Validate input
        if len(text) > 5000:
            return [TextContent(
                type="text",
                text="❌ Text too long. Maximum 5000 characters allowed."
            )]
        
        voice_id = voice_id or self.config.default_voice
        model = model or self.config.default_model
        voice_settings = voice_settings or {
            "stability": 0.5,
            "similarity_boost": 0.5,
            "style": 0.0
        }
        
        try:
            # Calculate cost
            character_count = len(text)
            base_cost = Decimal(str(character_count * 0.0001))  # $0.0001 per character
            final_cost = await self.credit_manager.calculate_media_cost(
                'audio', float(base_cost), 'basic'  # TODO: Get user tier
            )
            
            # Check user credits
            user_credits = await self.credit_manager.get_user_balance(user_id)
            if user_credits < final_cost:
                return [TextContent(
                    type="text",
                    text=f"❌ Insufficient credits.\n💰 Required: ${final_cost:.4f}\n💳 Available: ${user_credits:.4f}\n\n💡 Purchase more credits to continue."
                )]
            
            # Generate audio
            audio_data, duration = await self._generate_audio(text, voice_id, model, voice_settings)
            
            # Upload to storage (using Suna's existing storage system)
            audio_url = await self._upload_audio(audio_data, user_id)
            
            # Deduct credits
            await self.credit_manager.deduct_media_credits(
                user_id, 
                final_cost, 
                'audio',
                {
                    'text_length': character_count,
                    'voice_id': voice_id,
                    'model': model,
                    'duration': duration
                }
            )
            
            return [TextContent(
                type="text",
                text=f"🎵 **Audio Generated Successfully!**\n\n"
                     f"🔗 **Audio URL**: {audio_url}\n"
                     f"⏱️ **Duration**: {duration:.1f} seconds\n"
                     f"🎤 **Voice**: {voice_id}\n"
                     f"🤖 **Model**: {model}\n"
                     f"💰 **Cost**: ${final_cost:.4f}\n"
                     f"📝 **Characters**: {character_count}\n\n"
                     f"*Audio is ready to play in the chat!*"
            )]
            
        except Exception as e:
            logger.error(f"ElevenLabs TTS error: {str(e)}")
            return [TextContent(
                type="text",
                text=f"❌ Failed to generate audio: {str(e)}"
            )]
    
    async def get_voices(self) -> Sequence[TextContent]:
        """Get available voices from ElevenLabs"""
        try:
            async with self.session.get(
                f"{self.config.base_url}/voices",
                headers={"xi-api-key": self.config.api_key}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")
                
                data = await response.json()
                voices = data.get('voices', [])
                
                voice_list = "🎤 **Available ElevenLabs Voices:**\n\n"
                for voice in voices[:10]:  # Limit to first 10 voices
                    voice_list += f"• **{voice['name']}** (`{voice['voice_id']}`)\n"
                    voice_list += f"  - Category: {voice.get('category', 'Unknown')}\n"
                    voice_list += f"  - Description: {voice.get('description', 'No description')}\n\n"
                
                voice_list += f"\n📊 Total voices available: {len(voices)}"
                
                return [TextContent(type="text", text=voice_list)]
                
        except Exception as e:
            logger.error(f"ElevenLabs get_voices error: {str(e)}")
            return [TextContent(
                type="text",
                text=f"❌ Failed to fetch voices: {str(e)}"
            )]
    
    async def clone_voice(self, name: str, audio_files: list, user_id: str, description: str = "") -> Sequence[TextContent]:
        """Clone a voice from audio samples"""
        try:
            # Calculate cost for voice cloning (higher cost)
            base_cost = Decimal('5.00')  # $5 base cost for voice cloning
            final_cost = await self.credit_manager.calculate_media_cost(
                'audio', float(base_cost), 'basic'
            )
            
            # Check credits
            user_credits = await self.credit_manager.get_user_balance(user_id)
            if user_credits < final_cost:
                return [TextContent(
                    type="text",
                    text=f"❌ Insufficient credits for voice cloning.\n💰 Required: ${final_cost:.2f}\n💳 Available: ${user_credits:.2f}"
                )]
            
            # Prepare files for upload
            files = []
            for i, audio_b64 in enumerate(audio_files):
                audio_data = base64.b64decode(audio_b64)
                files.append(('files', (f'sample_{i}.wav', audio_data, 'audio/wav')))
            
            # Clone voice
            data = aiohttp.FormData()
            data.add_field('name', name)
            data.add_field('description', description)
            
            for file_data in files:
                data.add_field(file_data[0], file_data[1][1], filename=file_data[1][0], content_type=file_data[1][2])
            
            async with self.session.post(
                f"{self.config.base_url}/voices/add",
                headers={"xi-api-key": self.config.api_key},
                data=data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Voice cloning failed: {error_text}")
                
                result = await response.json()
                voice_id = result.get('voice_id')
                
                # Deduct credits
                await self.credit_manager.deduct_media_credits(
                    user_id,
                    final_cost,
                    'audio',
                    {
                        'action': 'voice_cloning',
                        'voice_name': name,
                        'voice_id': voice_id,
                        'samples_count': len(audio_files)
                    }
                )
                
                return [TextContent(
                    type="text",
                    text=f"🎭 **Voice Cloned Successfully!**\n\n"
                         f"🎤 **Voice Name**: {name}\n"
                         f"🆔 **Voice ID**: `{voice_id}`\n"
                         f"📝 **Description**: {description}\n"
                         f"💰 **Cost**: ${final_cost:.2f}\n\n"
                         f"*You can now use this voice ID for text-to-speech generation!*"
                )]
                
        except Exception as e:
            logger.error(f"ElevenLabs voice cloning error: {str(e)}")
            return [TextContent(
                type="text",
                text=f"❌ Voice cloning failed: {str(e)}"
            )]
    
    async def estimate_cost(self, text: str, model: str = None) -> Sequence[TextContent]:
        """Estimate cost for text-to-speech generation"""
        model = model or self.config.default_model
        character_count = len(text)
        base_cost = Decimal(str(character_count * 0.0001))
        final_cost = await self.credit_manager.calculate_media_cost('audio', float(base_cost), 'basic')
        
        return [TextContent(
            type="text",
            text=f"💰 **Cost Estimation**\n\n"
                 f"📝 **Text Length**: {character_count} characters\n"
                 f"🤖 **Model**: {model}\n"
                 f"💵 **Base Cost**: ${float(base_cost):.4f}\n"
                 f"💰 **Final Cost**: ${final_cost:.4f} (includes markup)\n"
                 f"⏱️ **Estimated Duration**: {self._estimate_duration(text):.1f} seconds"
        )]
    
    async def _generate_audio(self, text: str, voice_id: str, model: str, voice_settings: dict) -> tuple[bytes, float]:
        """Generate audio using ElevenLabs API"""
        payload = {
            "text": text,
            "model_id": model,
            "voice_settings": voice_settings
        }
        
        async with self.session.post(
            f"{self.config.base_url}/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": self.config.api_key,
                "Content-Type": "application/json"
            },
            json=payload
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"ElevenLabs API error {response.status}: {error_text}")
            
            audio_data = await response.read()
            duration = self._estimate_duration(text)
            
            return audio_data, duration
    
    async def _upload_audio(self, audio_data: bytes, user_id: str) -> str:
        """Upload audio to Suna's storage system"""
        # TODO: Integrate with Suna's existing S3/storage system
        # For now, return a placeholder URL
        import uuid
        filename = f"audio_{user_id}_{uuid.uuid4().hex[:8]}.mp3"
        
        # This should integrate with Suna's existing storage
        # from utils.s3_upload_utils import upload_file
        # audio_url = await upload_file(audio_data, filename)
        
        # Placeholder implementation
        audio_url = f"https://storage.suna.ai/audio/{filename}"
        
        return audio_url
    
    def _estimate_duration(self, text: str) -> float:
        """Estimate audio duration based on text length"""
        # Average speaking rate: ~150 words per minute
        words = len(text.split())
        duration = (words / 150) * 60  # Convert to seconds
        return max(1.0, duration)  # Minimum 1 second

async def main():
    """Main function to run the ElevenLabs MCP Server"""
    config = ElevenLabsConfig(
        api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        base_url=os.getenv("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io/v1")
    )
    
    if not config.api_key:
        logger.error("ELEVENLABS_API_KEY environment variable is required")
        return
    
    async with ElevenLabsMCPServer(config) as server:
        logger.info("Starting ElevenLabs MCP Server...")
        await server.server.run()

if __name__ == "__main__":
    asyncio.run(main())