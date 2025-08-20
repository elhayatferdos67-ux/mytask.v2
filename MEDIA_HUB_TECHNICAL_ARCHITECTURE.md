# البنية التقنية لـ Media AI Services Hub

## نظرة عامة على البنية

```
┌─────────────────────────────────────────────────────────────┐
│                    Suna AI Frontend                        │
├─────────────────────────────────────────────────────────────┤
│  Chat Interface  │  Media Hub  │  Credit Dashboard  │ IDE  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Gateway & Router                     │
├─────────────────────────────────────────────────────────────┤
│  Authentication  │  Rate Limiting  │  Request Routing      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                Media Services Orchestrator                 │
├─────────────────────────────────────────────────────────────┤
│  Provider Selection  │  Cost Calculation  │  Queue Manager │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Provider Integrations                    │
├─────────────────────────────────────────────────────────────┤
│  Video APIs  │  Audio APIs  │  Image APIs  │  Design APIs  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Storage & Content Delivery                    │
├─────────────────────────────────────────────────────────────┤
│  Media Storage  │  CDN  │  Metadata DB  │  Cache Layer    │
└─────────────────────────────────────────────────────────────┘
```

## 1. Core Backend Components

### Media Services Manager

```python
# backend/services/media_hub/media_services_manager.py
from typing import Dict, List, Optional, Any
from enum import Enum
import asyncio
from dataclasses import dataclass

class MediaType(Enum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    DESIGN = "design"
    MODEL_3D = "3d"

class ProviderStatus(Enum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    DISABLED = "disabled"

@dataclass
class MediaRequest:
    user_id: str
    media_type: MediaType
    prompt: str
    parameters: Dict[str, Any]
    max_cost: Optional[float] = None
    priority: int = 1

@dataclass
class MediaResponse:
    request_id: str
    media_url: str
    thumbnail_url: Optional[str]
    metadata: Dict[str, Any]
    cost: float
    provider: str
    generation_time: float

class MediaServicesManager:
    def __init__(self):
        self.providers = self._initialize_providers()
        self.credit_manager = CreditManager()
        self.queue_manager = QueueManager()
        self.storage_manager = MediaStorageManager()
        
    def _initialize_providers(self) -> Dict[MediaType, List[BaseProvider]]:
        return {
            MediaType.VIDEO: [
                VeoProvider(),
                KlingProvider(), 
                RunwayProvider(),
                PikaProvider()
            ],
            MediaType.AUDIO: [
                ElevenLabsProvider(),
                MurfProvider(),
                AzureSpeechProvider()
            ],
            MediaType.IMAGE: [
                DalleProvider(),
                StableDiffusionProvider(),
                MidjourneyProvider()
            ],
            MediaType.DESIGN: [
                CanvaProvider(),
                AdobeExpressProvider(),
                FigmaProvider()
            ],
            MediaType.MODEL_3D: [
                SplineProvider(),
                LumaProvider(),
                KaedimProvider()
            ]
        }
    
    async def generate_media(self, request: MediaRequest) -> MediaResponse:
        """Main method for media generation"""
        try:
            # 1. Validate user credits
            await self._validate_credits(request)
            
            # 2. Select best provider
            provider = await self._select_provider(request)
            
            # 3. Estimate cost
            estimated_cost = await provider.estimate_cost(request)
            
            # 4. Reserve credits
            await self.credit_manager.reserve_credits(
                request.user_id, estimated_cost
            )
            
            # 5. Add to queue
            job_id = await self.queue_manager.add_job(request, provider)
            
            # 6. Execute generation
            response = await self._execute_generation(job_id, request, provider)
            
            # 7. Process and store result
            final_response = await self._process_result(response, request)
            
            return final_response
            
        except Exception as e:
            await self._handle_error(request, e)
            raise
    
    async def _select_provider(self, request: MediaRequest) -> BaseProvider:
        """Smart provider selection based on multiple factors"""
        available_providers = [
            p for p in self.providers[request.media_type]
            if p.status == ProviderStatus.ACTIVE
        ]
        
        if not available_providers:
            raise NoProvidersAvailableError(request.media_type)
        
        # Score providers based on:
        # - Cost efficiency
        # - Quality rating
        # - Response time
        # - Current load
        scored_providers = []
        
        for provider in available_providers:
            score = await self._calculate_provider_score(provider, request)
            scored_providers.append((provider, score))
        
        # Sort by score (highest first)
        scored_providers.sort(key=lambda x: x[1], reverse=True)
        
        return scored_providers[0][0]
    
    async def _calculate_provider_score(
        self, provider: BaseProvider, request: MediaRequest
    ) -> float:
        """Calculate provider score for selection"""
        cost_score = await provider.get_cost_efficiency_score(request)
        quality_score = provider.quality_rating
        speed_score = await provider.get_speed_score()
        load_score = await provider.get_current_load_score()
        
        # Weighted scoring
        total_score = (
            cost_score * 0.3 +
            quality_score * 0.4 +
            speed_score * 0.2 +
            load_score * 0.1
        )
        
        return total_score
```

### Credit Management System

```python
# backend/services/media_hub/credit_manager.py
from decimal import Decimal
from typing import Dict, List
import asyncio

class CreditManager:
    def __init__(self):
        self.db = get_database()
        self.redis = get_redis_client()
        
    async def get_user_balance(self, user_id: str) -> Decimal:
        """Get user's current credit balance"""
        balance = await self.db.fetch_one(
            "SELECT balance FROM user_credits WHERE user_id = ?",
            (user_id,)
        )
        return Decimal(balance['balance']) if balance else Decimal('0')
    
    async def reserve_credits(self, user_id: str, amount: Decimal) -> str:
        """Reserve credits for a transaction"""
        reservation_id = generate_uuid()
        
        async with self.db.transaction():
            current_balance = await self.get_user_balance(user_id)
            
            if current_balance < amount:
                raise InsufficientCreditsError(current_balance, amount)
            
            # Create reservation
            await self.db.execute(
                """INSERT INTO credit_reservations 
                   (id, user_id, amount, status, created_at)
                   VALUES (?, ?, ?, 'reserved', NOW())""",
                (reservation_id, user_id, amount)
            )
            
            # Update available balance
            await self.db.execute(
                """UPDATE user_credits 
                   SET reserved_balance = reserved_balance + ?
                   WHERE user_id = ?""",
                (amount, user_id)
            )
        
        return reservation_id
    
    async def confirm_transaction(
        self, reservation_id: str, actual_cost: Decimal
    ) -> None:
        """Confirm and finalize credit transaction"""
        async with self.db.transaction():
            reservation = await self.db.fetch_one(
                "SELECT * FROM credit_reservations WHERE id = ?",
                (reservation_id,)
            )
            
            if not reservation:
                raise ReservationNotFoundError(reservation_id)
            
            user_id = reservation['user_id']
            reserved_amount = Decimal(reservation['amount'])
            
            # Calculate refund if actual cost is less
            refund = max(Decimal('0'), reserved_amount - actual_cost)
            
            # Update user balance
            await self.db.execute(
                """UPDATE user_credits 
                   SET balance = balance - ?,
                       reserved_balance = reserved_balance - ?
                   WHERE user_id = ?""",
                (actual_cost, reserved_amount, user_id)
            )
            
            # Log transaction
            await self.db.execute(
                """INSERT INTO credit_transactions
                   (user_id, amount, type, reservation_id, created_at)
                   VALUES (?, ?, 'debit', ?, NOW())""",
                (user_id, actual_cost, reservation_id)
            )
            
            # Update reservation status
            await self.db.execute(
                """UPDATE credit_reservations 
                   SET status = 'confirmed', actual_amount = ?
                   WHERE id = ?""",
                (actual_cost, reservation_id)
            )
    
    def calculate_markup(
        self, base_cost: Decimal, service_type: str, user_tier: str
    ) -> Decimal:
        """Calculate markup based on service type and user tier"""
        markup_rates = {
            'video': {'basic': 0.35, 'pro': 0.30, 'enterprise': 0.25},
            'audio': {'basic': 0.30, 'pro': 0.25, 'enterprise': 0.20},
            'image': {'basic': 0.25, 'pro': 0.20, 'enterprise': 0.15},
            'design': {'basic': 0.30, 'pro': 0.25, 'enterprise': 0.20},
            '3d': {'basic': 0.40, 'pro': 0.35, 'enterprise': 0.30}
        }
        
        rate = markup_rates.get(service_type, {}).get(user_tier, 0.30)
        markup = base_cost * Decimal(str(rate))
        
        return base_cost + markup
```

### Provider Integration Framework

```python
# backend/services/media_hub/providers/base_provider.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import aiohttp
import asyncio

class BaseProvider(ABC):
    def __init__(self, name: str, api_key: str, base_url: str):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url
        self.session = None
        self.status = ProviderStatus.ACTIVE
        self.quality_rating = 0.0
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=300)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def generate(self, request: MediaRequest) -> MediaResponse:
        """Generate media content"""
        pass
    
    @abstractmethod
    async def estimate_cost(self, request: MediaRequest) -> Decimal:
        """Estimate generation cost"""
        pass
    
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get provider status and health"""
        pass
    
    async def get_cost_efficiency_score(self, request: MediaRequest) -> float:
        """Calculate cost efficiency score (0-1)"""
        estimated_cost = await self.estimate_cost(request)
        # Compare with average market cost
        market_average = await self._get_market_average_cost(request)
        
        if market_average == 0:
            return 0.5
        
        efficiency = 1 - (float(estimated_cost) / float(market_average))
        return max(0, min(1, efficiency + 0.5))
    
    async def get_speed_score(self) -> float:
        """Get speed performance score"""
        # Implementation based on historical performance
        pass
    
    async def get_current_load_score(self) -> float:
        """Get current load score"""
        # Implementation based on queue length and response times
        pass

# Example: ElevenLabs Provider
class ElevenLabsProvider(BaseProvider):
    def __init__(self):
        super().__init__(
            name="ElevenLabs",
            api_key=settings.ELEVENLABS_API_KEY,
            base_url="https://api.elevenlabs.io/v1"
        )
        self.quality_rating = 0.95
    
    async def generate(self, request: MediaRequest) -> MediaResponse:
        """Generate audio using ElevenLabs API"""
        start_time = time.time()
        
        payload = {
            "text": request.prompt,
            "voice_id": request.parameters.get("voice_id", "default"),
            "model_id": request.parameters.get("model", "eleven_monolingual_v1"),
            "voice_settings": {
                "stability": request.parameters.get("stability", 0.5),
                "similarity_boost": request.parameters.get("similarity", 0.5)
            }
        }
        
        async with self.session.post(
            f"{self.base_url}/text-to-speech/{payload['voice_id']}",
            json=payload,
            headers={"xi-api-key": self.api_key}
        ) as response:
            if response.status != 200:
                error_data = await response.json()
                raise ProviderError(f"ElevenLabs API error: {error_data}")
            
            audio_data = await response.read()
            
        # Upload to storage
        media_url = await self.storage_manager.upload_audio(
            audio_data, f"{request.user_id}/{generate_uuid()}.mp3"
        )
        
        # Calculate actual cost
        character_count = len(request.prompt)
        base_cost = Decimal(str(character_count * 0.0001))  # $0.0001 per character
        
        generation_time = time.time() - start_time
        
        return MediaResponse(
            request_id=request.request_id,
            media_url=media_url,
            thumbnail_url=None,
            metadata={
                "duration": self._calculate_audio_duration(audio_data),
                "character_count": character_count,
                "voice_id": payload["voice_id"],
                "model": payload["model_id"]
            },
            cost=base_cost,
            provider=self.name,
            generation_time=generation_time
        )
    
    async def estimate_cost(self, request: MediaRequest) -> Decimal:
        """Estimate cost based on text length"""
        character_count = len(request.prompt)
        return Decimal(str(character_count * 0.0001))
```

## 2. Frontend Components

### Media Hub Interface

```typescript
// frontend/src/components/media-hub/MediaHub.tsx
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  Video, 
  Music, 
  Image, 
  Palette, 
  Box,
  CreditCard,
  Zap
} from 'lucide-react';

interface MediaHubProps {
  userId: string;
  creditBalance: number;
  onCreditUpdate: (newBalance: number) => void;
}

export const MediaHub: React.FC<MediaHubProps> = ({
  userId,
  creditBalance,
  onCreditUpdate
}) => {
  const [activeTab, setActiveTab] = useState('video');
  const [generationQueue, setGenerationQueue] = useState([]);
  const [recentGenerations, setRecentGenerations] = useState([]);

  const mediaTypes = [
    { id: 'video', label: 'Video', icon: Video, color: 'bg-red-500' },
    { id: 'audio', label: 'Audio', icon: Music, color: 'bg-green-500' },
    { id: 'image', label: 'Images', icon: Image, color: 'bg-blue-500' },
    { id: 'design', label: 'Design', icon: Palette, color: 'bg-purple-500' },
    { id: '3d', label: '3D Models', icon: Box, color: 'bg-orange-500' }
  ];

  return (
    <div className="media-hub-container">
      {/* Credit Balance Header */}
      <Card className="mb-6">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            Credit Balance
          </CardTitle>
          <div className="flex items-center gap-4">
            <Badge variant="secondary" className="text-lg px-3 py-1">
              {creditBalance.toLocaleString()} Credits
            </Badge>
            <Button variant="outline" size="sm">
              Buy Credits
            </Button>
          </div>
        </CardHeader>
      </Card>

      {/* Media Type Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5">
          {mediaTypes.map((type) => (
            <TabsTrigger key={type.id} value={type.id} className="flex items-center gap-2">
              <type.icon className="h-4 w-4" />
              {type.label}
            </TabsTrigger>
          ))}
        </TabsList>

        {/* Video Generation */}
        <TabsContent value="video">
          <VideoGenerationPanel 
            userId={userId}
            creditBalance={creditBalance}
            onGenerate={handleVideoGeneration}
          />
        </TabsContent>

        {/* Audio Generation */}
        <TabsContent value="audio">
          <AudioGenerationPanel 
            userId={userId}
            creditBalance={creditBalance}
            onGenerate={handleAudioGeneration}
          />
        </TabsContent>

        {/* Other tabs... */}
      </Tabs>

      {/* Generation Queue */}
      {generationQueue.length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              Generation Queue
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {generationQueue.map((job) => (
                <GenerationQueueItem key={job.id} job={job} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Generations */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Recent Generations</CardTitle>
        </CardHeader>
        <CardContent>
          <MediaGallery items={recentGenerations} />
        </CardContent>
      </Card>
    </div>
  );
};
```

### Video Generation Panel

```typescript
// frontend/src/components/media-hub/VideoGenerationPanel.tsx
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, Play } from 'lucide-react';

interface VideoGenerationPanelProps {
  userId: string;
  creditBalance: number;
  onGenerate: (request: VideoGenerationRequest) => void;
}

export const VideoGenerationPanel: React.FC<VideoGenerationPanelProps> = ({
  userId,
  creditBalance,
  onGenerate
}) => {
  const [prompt, setPrompt] = useState('');
  const [duration, setDuration] = useState([5]);
  const [quality, setQuality] = useState('standard');
  const [provider, setProvider] = useState('auto');
  const [estimatedCost, setEstimatedCost] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);

  const providers = [
    { id: 'auto', name: 'Auto Select (Best Value)', cost: 1.0 },
    { id: 'veo3', name: 'Google Veo 3 (Premium)', cost: 1.5 },
    { id: 'kling', name: 'Kling AI (Balanced)', cost: 1.2 },
    { id: 'runway', name: 'Runway ML (Creative)', cost: 1.3 },
    { id: 'pika', name: 'Pika Labs (Fast)', cost: 0.8 }
  ];

  const qualityOptions = [
    { id: 'draft', name: 'Draft (480p)', multiplier: 0.5 },
    { id: 'standard', name: 'Standard (720p)', multiplier: 1.0 },
    { id: 'hd', name: 'HD (1080p)', multiplier: 1.5 },
    { id: '4k', name: '4K (2160p)', multiplier: 3.0 }
  ];

  useEffect(() => {
    calculateEstimatedCost();
  }, [prompt, duration, quality, provider]);

  const calculateEstimatedCost = async () => {
    if (!prompt.trim()) {
      setEstimatedCost(0);
      return;
    }

    const baseCost = duration[0] * 10; // 10 credits per second
    const qualityMultiplier = qualityOptions.find(q => q.id === quality)?.multiplier || 1;
    const providerMultiplier = providers.find(p => p.id === provider)?.cost || 1;
    
    const estimated = Math.ceil(baseCost * qualityMultiplier * providerMultiplier);
    setEstimatedCost(estimated);
  };

  const handleGenerate = async () => {
    if (!prompt.trim() || estimatedCost > creditBalance) return;

    setIsGenerating(true);
    
    try {
      await onGenerate({
        prompt,
        duration: duration[0],
        quality,
        provider: provider === 'auto' ? null : provider,
        estimatedCost
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const canGenerate = prompt.trim() && estimatedCost <= creditBalance && !isGenerating;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Play className="h-5 w-5" />
          Video Generation
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Prompt Input */}
        <div>
          <label className="text-sm font-medium mb-2 block">
            Video Description
          </label>
          <Textarea
            placeholder="Describe the video you want to generate..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={4}
            className="resize-none"
          />
        </div>

        {/* Duration Slider */}
        <div>
          <label className="text-sm font-medium mb-2 block">
            Duration: {duration[0]} seconds
          </label>
          <Slider
            value={duration}
            onValueChange={setDuration}
            max={30}
            min={1}
            step={1}
            className="w-full"
          />
        </div>

        {/* Quality Selection */}
        <div>
          <label className="text-sm font-medium mb-2 block">Quality</label>
          <Select value={quality} onValueChange={setQuality}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {qualityOptions.map((option) => (
                <SelectItem key={option.id} value={option.id}>
                  {option.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Provider Selection */}
        <div>
          <label className="text-sm font-medium mb-2 block">Provider</label>
          <Select value={provider} onValueChange={setProvider}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {providers.map((prov) => (
                <SelectItem key={prov.id} value={prov.id}>
                  {prov.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Cost Estimation */}
        <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
          <div>
            <p className="text-sm font-medium">Estimated Cost</p>
            <p className="text-xs text-muted-foreground">
              Based on current settings
            </p>
          </div>
          <Badge variant={estimatedCost > creditBalance ? "destructive" : "secondary"}>
            {estimatedCost} Credits
          </Badge>
        </div>

        {/* Insufficient Credits Warning */}
        {estimatedCost > creditBalance && (
          <div className="flex items-center gap-2 p-3 bg-destructive/10 text-destructive rounded-lg">
            <AlertCircle className="h-4 w-4" />
            <span className="text-sm">
              Insufficient credits. You need {estimatedCost - creditBalance} more credits.
            </span>
          </div>
        )}

        {/* Generate Button */}
        <Button 
          onClick={handleGenerate}
          disabled={!canGenerate}
          className="w-full"
          size="lg"
        >
          {isGenerating ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
              Generating Video...
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-2" />
              Generate Video ({estimatedCost} Credits)
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
};
```

### Media Viewer Component

```typescript
// frontend/src/components/media-hub/MediaViewer.tsx
import React, { useState, useRef } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Download, 
  Share2, 
  Play, 
  Pause, 
  Volume2, 
  VolumeX,
  Maximize,
  RotateCcw
} from 'lucide-react';

interface MediaViewerProps {
  media: {
    id: string;
    type: 'video' | 'audio' | 'image' | '3d';
    url: string;
    thumbnailUrl?: string;
    metadata: any;
    cost: number;
    createdAt: string;
  };
  onDownload?: (mediaId: string) => void;
  onShare?: (mediaId: string) => void;
}

export const MediaViewer: React.FC<MediaViewerProps> = ({
  media,
  onDownload,
  onShare
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const mediaRef = useRef<HTMLVideoElement | HTMLAudioElement>(null);

  const handlePlayPause = () => {
    if (mediaRef.current) {
      if (isPlaying) {
        mediaRef.current.pause();
      } else {
        mediaRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleMuteToggle = () => {
    if (mediaRef.current) {
      mediaRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const renderMediaContent = () => {
    switch (media.type) {
      case 'video':
        return (
          <div className="relative group">
            <video
              ref={mediaRef as React.RefObject<HTMLVideoElement>}
              src={media.url}
              poster={media.thumbnailUrl}
              className="w-full h-auto rounded-lg"
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              controls
            />
            
            {/* Custom Controls Overlay */}
            <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/20 rounded-lg">
              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handlePlayPause}
                >
                  {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleMuteToggle}
                >
                  {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setIsFullscreen(true)}
                >
                  <Maximize className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        );

      case 'audio':
        return (
          <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white">
            <audio
              ref={mediaRef as React.RefObject<HTMLAudioElement>}
              src={media.url}
              className="w-full"
              controls
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
            />
            
            {/* Audio Visualization Placeholder */}
            <div className="mt-4 flex items-center justify-center">
              <div className="flex items-end gap-1">
                {Array.from({ length: 20 }).map((_, i) => (
                  <div
                    key={i}
                    className={`bg-white/60 rounded-full transition-all duration-300 ${
                      isPlaying ? 'animate-pulse' : ''
                    }`}
                    style={{
                      width: '3px',
                      height: `${Math.random() * 30 + 10}px`
                    }}
                  />
                ))}
              </div>
            </div>
          </div>
        );

      case 'image':
        return (
          <div className="relative group">
            <img
              src={media.url}
              alt="Generated content"
              className="w-full h-auto rounded-lg cursor-zoom-in"
              onClick={() => setIsFullscreen(true)}
            />
            
            {/* Image Overlay */}
            <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/20 rounded-lg">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setIsFullscreen(true)}
              >
                <Maximize className="h-4 w-4" />
              </Button>
            </div>
          </div>
        );

      case '3d':
        return (
          <div className="bg-gray-100 rounded-lg p-6 text-center">
            <div className="w-full h-64 bg-gray-200 rounded-lg flex items-center justify-center">
              {/* 3D Model Viewer Placeholder */}
              <div className="text-gray-500">
                <RotateCcw className="h-8 w-8 mx-auto mb-2" />
                <p>3D Model Viewer</p>
                <p className="text-sm">Click to interact</p>
              </div>
            </div>
          </div>
        );

      default:
        return <div>Unsupported media type</div>;
    }
  };

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-0">
        {/* Media Content */}
        {renderMediaContent()}
        
        {/* Media Info & Actions */}
        <div className="p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="capitalize">
                {media.type}
              </Badge>
              <Badge variant="outline">
                {media.cost} Credits
              </Badge>
            </div>
            <div className="text-sm text-muted-foreground">
              {new Date(media.createdAt).toLocaleDateString()}
            </div>
          </div>
          
          {/* Metadata */}
          {media.metadata && (
            <div className="text-sm text-muted-foreground mb-3">
              {media.type === 'video' && (
                <p>Duration: {media.metadata.duration}s • Quality: {media.metadata.quality}</p>
              )}
              {media.type === 'audio' && (
                <p>Duration: {media.metadata.duration}s • Voice: {media.metadata.voice}</p>
              )}
              {media.type === 'image' && (
                <p>Size: {media.metadata.width}×{media.metadata.height} • Style: {media.metadata.style}</p>
              )}
            </div>
          )}
          
          {/* Action Buttons */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onDownload?.(media.id)}
            >
              <Download className="h-4 w-4 mr-1" />
              Download
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onShare?.(media.id)}
            >
              <Share2 className="h-4 w-4 mr-1" />
              Share
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
```

## 3. Database Schema

```sql
-- Credit Management Tables
CREATE TABLE user_credits (
    user_id VARCHAR(255) PRIMARY KEY,
    balance DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    reserved_balance DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total_spent DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE credit_transactions (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    type ENUM('credit', 'debit') NOT NULL,
    description TEXT,
    reservation_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_created (user_id, created_at)
);

CREATE TABLE credit_reservations (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    actual_amount DECIMAL(10,2),
    status ENUM('reserved', 'confirmed', 'cancelled') NOT NULL,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Media Generation Tables
CREATE TABLE media_generations (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    media_type ENUM('video', 'audio', 'image', 'design', '3d') NOT NULL,
    provider VARCHAR(100) NOT NULL,
    prompt TEXT NOT NULL,
    parameters JSON,
    status ENUM('queued', 'processing', 'completed', 'failed') NOT NULL,
    media_url VARCHAR(500),
    thumbnail_url VARCHAR(500),
    metadata JSON,
    cost DECIMAL(8,4) NOT NULL,
    generation_time FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_created (user_id, created_at),
    INDEX idx_status (status)
);

-- Provider Management Tables
CREATE TABLE media_providers (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    media_type ENUM('video', 'audio', 'image', 'design', '3d') NOT NULL,
    status ENUM('active', 'maintenance', 'disabled') NOT NULL,
    api_endpoint VARCHAR(500),
    quality_rating DECIMAL(3,2) DEFAULT 0.00,
    cost_per_unit DECIMAL(8,6),
    rate_limit_per_minute INT DEFAULT 60,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Usage Analytics Tables
CREATE TABLE usage_analytics (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    media_type ENUM('video', 'audio', 'image', 'design', '3d') NOT NULL,
    provider VARCHAR(100) NOT NULL,
    cost DECIMAL(8,4) NOT NULL,
    generation_time FLOAT,
    success BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_date (user_id, created_at),
    INDEX idx_provider_date (provider, created_at)
);
```

## 4. API Endpoints

```python
# backend/api/media_hub.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional
import asyncio

router = APIRouter(prefix="/api/media-hub", tags=["media-hub"])

@router.get("/providers")
async def get_providers(
    media_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get available providers for media generation"""
    providers = await media_manager.get_available_providers(media_type)
    return {"providers": providers}

@router.post("/generate")
async def generate_media(
    request: MediaGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Generate media content"""
    try:
        # Validate credits
        user_balance = await credit_manager.get_user_balance(current_user.id)
        estimated_cost = await media_manager.estimate_cost(request)
        
        if user_balance < estimated_cost:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Required: {estimated_cost}, Available: {user_balance}"
            )
        
        # Start generation process
        job_id = await media_manager.start_generation(
            user_id=current_user.id,
            request=request
        )
        
        return {
            "job_id": job_id,
            "estimated_cost": estimated_cost,
            "status": "queued"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/generations/{job_id}")
async def get_generation_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get generation job status"""
    job = await media_manager.get_job_status(job_id, current_user.id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job

@router.get("/generations")
async def get_user_generations(
    limit: int = 20,
    offset: int = 0,
    media_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get user's media generations"""
    generations = await media_manager.get_user_generations(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        media_type=media_type
    )
    
    return {"generations": generations}

@router.get("/credits/balance")
async def get_credit_balance(
    current_user: User = Depends(get_current_user)
):
    """Get user's credit balance"""
    balance = await credit_manager.get_user_balance(current_user.id)
    return {"balance": float(balance)}

@router.post("/credits/purchase")
async def purchase_credits(
    package: CreditPackage,
    current_user: User = Depends(get_current_user)
):
    """Purchase credit package"""
    # Integration with payment processor
    payment_result = await payment_processor.process_payment(
        user_id=current_user.id,
        amount=package.price,
        credits=package.credits
    )
    
    if payment_result.success:
        await credit_manager.add_credits(
            user_id=current_user.id,
            amount=package.credits,
            transaction_id=payment_result.transaction_id
        )
        
        return {
            "success": True,
            "credits_added": package.credits,
            "new_balance": await credit_manager.get_user_balance(current_user.id)
        }
    else:
        raise HTTPException(
            status_code=402,
            detail="Payment failed"
        )
```

هذه البنية التقنية توفر أساساً قوياً لتنفيذ Media AI Services Hub في Suna AI، مع التركيز على الأداء، القابلية للتوسع، وتجربة المستخدم المتميزة.