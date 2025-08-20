'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { 
  Play, 
  Pause, 
  Volume2, 
  VolumeX, 
  Download, 
  Share2, 
  Edit,
  Maximize,
  RotateCcw,
  ZoomIn,
  ZoomOut
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface MediaMetadata {
  duration?: number;
  cost?: number;
  provider?: string;
  model?: string;
  voice_id?: string;
  width?: number;
  height?: number;
  size?: number;
  format?: string;
}

interface MediaViewerProps {
  type: 'video' | 'audio' | 'image' | '3d' | 'design';
  url: string;
  thumbnailUrl?: string;
  metadata?: MediaMetadata;
  className?: string;
  onEdit?: () => void;
  onDownload?: () => void;
  onShare?: () => void;
}

export const MediaViewer: React.FC<MediaViewerProps> = ({ 
  type, 
  url, 
  thumbnailUrl,
  metadata = {},
  className,
  onEdit,
  onDownload,
  onShare
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [volume, setVolume] = useState(1);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const mediaRef = useRef<HTMLVideoElement | HTMLAudioElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const media = mediaRef.current;
    if (!media) return;

    const handleLoadedData = () => {
      setIsLoading(false);
      setDuration(media.duration);
    };

    const handleTimeUpdate = () => {
      setCurrentTime(media.currentTime);
    };

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleError = () => {
      setError('Failed to load media');
      setIsLoading(false);
    };

    media.addEventListener('loadeddata', handleLoadedData);
    media.addEventListener('timeupdate', handleTimeUpdate);
    media.addEventListener('play', handlePlay);
    media.addEventListener('pause', handlePause);
    media.addEventListener('error', handleError);

    return () => {
      media.removeEventListener('loadeddata', handleLoadedData);
      media.removeEventListener('timeupdate', handleTimeUpdate);
      media.removeEventListener('play', handlePlay);
      media.removeEventListener('pause', handlePause);
      media.removeEventListener('error', handleError);
    };
  }, []);

  const handlePlayPause = () => {
    const media = mediaRef.current;
    if (!media) return;

    if (isPlaying) {
      media.pause();
    } else {
      media.play().catch(err => {
        console.error('Play failed:', err);
        toast.error('Failed to play media');
      });
    }
  };

  const handleMuteToggle = () => {
    const media = mediaRef.current;
    if (!media) return;

    media.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const handleVolumeChange = (newVolume: number) => {
    const media = mediaRef.current;
    if (!media) return;

    media.volume = newVolume;
    setVolume(newVolume);
    setIsMuted(newVolume === 0);
  };

  const handleSeek = (time: number) => {
    const media = mediaRef.current;
    if (!media) return;

    media.currentTime = time;
    setCurrentTime(time);
  };

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const handleDownload = async () => {
    try {
      const response = await fetch(url);
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `media_${Date.now()}.${type === 'audio' ? 'mp3' : type === 'video' ? 'mp4' : 'png'}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      toast.success('Download started');
    } catch (error) {
      console.error('Download failed:', error);
      toast.error('Download failed');
    }
  };

  const handleShare = async () => {
    try {
      if (navigator.share) {
        await navigator.share({
          title: `Generated ${type}`,
          url: url
        });
      } else {
        await navigator.clipboard.writeText(url);
        toast.success('URL copied to clipboard');
      }
    } catch (error) {
      console.error('Share failed:', error);
      toast.error('Share failed');
    }
  };

  const renderVideoPlayer = () => (
    <div className="relative group bg-black rounded-lg overflow-hidden">
      <video
        ref={mediaRef as React.RefObject<HTMLVideoElement>}
        src={url}
        poster={thumbnailUrl}
        className="w-full h-auto"
        preload="metadata"
      />
      
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white" />
        </div>
      )}

      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50 text-white">
          <p>{error}</p>
        </div>
      )}

      {/* Video Controls */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4 opacity-0 group-hover:opacity-100 transition-opacity">
        <div className="flex items-center gap-2 mb-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handlePlayPause}
            className="text-white hover:bg-white/20"
          >
            {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </Button>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={handleMuteToggle}
            className="text-white hover:bg-white/20"
          >
            {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
          </Button>

          <div className="flex-1 mx-2">
            <input
              type="range"
              min="0"
              max={duration}
              value={currentTime}
              onChange={(e) => handleSeek(Number(e.target.value))}
              className="w-full h-1 bg-white/30 rounded-lg appearance-none cursor-pointer"
            />
          </div>

          <span className="text-white text-sm">
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsFullscreen(true)}
            className="text-white hover:bg-white/20"
          >
            <Maximize className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );

  const renderAudioPlayer = () => (
    <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white">
      <audio
        ref={mediaRef as React.RefObject<HTMLAudioElement>}
        src={url}
        preload="metadata"
        className="hidden"
      />
      
      {/* Audio Visualization */}
      <div className="flex items-center justify-center mb-4">
        <div className="flex items-end gap-1">
          {Array.from({ length: 20 }).map((_, i) => (
            <div
              key={i}
              className={cn(
                "bg-white/60 rounded-full transition-all duration-300",
                isPlaying && "animate-pulse"
              )}
              style={{
                width: '3px',
                height: `${Math.random() * 30 + 10}px`,
                animationDelay: `${i * 0.1}s`
              }}
            />
          ))}
        </div>
      </div>

      {/* Audio Controls */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          onClick={handlePlayPause}
          className="text-white hover:bg-white/20"
        >
          {isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
        </Button>

        <div className="flex-1">
          <input
            type="range"
            min="0"
            max={duration}
            value={currentTime}
            onChange={(e) => handleSeek(Number(e.target.value))}
            className="w-full h-2 bg-white/30 rounded-lg appearance-none cursor-pointer"
          />
        </div>

        <span className="text-sm opacity-80">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>

        <Button
          variant="ghost"
          onClick={handleMuteToggle}
          className="text-white hover:bg-white/20"
        >
          {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
        </Button>
      </div>

      {/* Metadata */}
      {metadata.voice_id && (
        <div className="mt-4 text-sm opacity-80">
          Voice: {metadata.voice_id} • Model: {metadata.model}
        </div>
      )}
    </div>
  );

  const renderImageViewer = () => (
    <div className="relative group">
      <img 
        src={url} 
        alt="Generated content" 
        className="w-full h-auto rounded-lg cursor-pointer transition-transform hover:scale-[1.02]"
        onClick={() => setIsFullscreen(true)}
        onLoad={() => setIsLoading(false)}
        onError={() => setError('Failed to load image')}
      />
      
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100 rounded-lg">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-400" />
        </div>
      )}

      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100 rounded-lg">
          <p className="text-gray-500">{error}</p>
        </div>
      )}

      {/* Image Overlay */}
      <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/20 rounded-lg">
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setIsFullscreen(true)}
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
          {onEdit && (
            <Button
              variant="secondary"
              size="sm"
              onClick={onEdit}
            >
              <Edit className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Image Info */}
      {metadata.width && metadata.height && (
        <div className="absolute top-2 right-2 bg-black/50 text-white text-xs px-2 py-1 rounded">
          {metadata.width} × {metadata.height}
        </div>
      )}
    </div>
  );

  const render3DViewer = () => (
    <div className="bg-gray-100 rounded-lg p-6 text-center min-h-[300px] flex items-center justify-center">
      <div className="text-gray-500">
        <RotateCcw className="h-12 w-12 mx-auto mb-4 animate-spin" />
        <h3 className="text-lg font-medium mb-2">3D Model Viewer</h3>
        <p className="text-sm">Interactive 3D model loading...</p>
        <Button 
          variant="outline" 
          className="mt-4"
          onClick={() => setIsFullscreen(true)}
        >
          View in Full Screen
        </Button>
      </div>
    </div>
  );

  const renderDesignViewer = () => (
    <div className="relative group">
      <img 
        src={url} 
        alt="Design preview" 
        className="w-full h-auto rounded-lg cursor-pointer"
        onClick={() => setIsFullscreen(true)}
      />
      
      <div className="absolute top-2 left-2 bg-black/50 text-white text-xs px-2 py-1 rounded">
        Design
      </div>
      
      {onEdit && (
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/20 rounded-lg">
          <Button
            variant="secondary"
            onClick={onEdit}
          >
            <Edit className="h-4 w-4 mr-2" />
            Edit Design
          </Button>
        </div>
      )}
    </div>
  );

  const renderMediaContent = () => {
    switch (type) {
      case 'video':
        return renderVideoPlayer();
      case 'audio':
        return renderAudioPlayer();
      case 'image':
        return renderImageViewer();
      case '3d':
        return render3DViewer();
      case 'design':
        return renderDesignViewer();
      default:
        return <div className="p-4 text-center text-gray-500">Unsupported media type: {type}</div>;
    }
  };

  return (
    <>
      <Card className={cn("overflow-hidden", className)}>
        <CardContent className="p-0">
          {renderMediaContent()}
          
          {/* Media Info & Actions */}
          <div className="p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="capitalize">
                  {type}
                </Badge>
                {metadata.cost && (
                  <Badge variant="outline">
                    ${metadata.cost.toFixed(4)}
                  </Badge>
                )}
                {metadata.provider && (
                  <Badge variant="outline">
                    {metadata.provider}
                  </Badge>
                )}
              </div>
              <div className="text-sm text-muted-foreground">
                {metadata.duration && `${metadata.duration.toFixed(1)}s`}
                {metadata.size && ` • ${(metadata.size / 1024 / 1024).toFixed(1)}MB`}
              </div>
            </div>
            
            {/* Action Buttons */}
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onDownload || handleDownload}
              >
                <Download className="h-4 w-4 mr-1" />
                Download
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={onShare || handleShare}
              >
                <Share2 className="h-4 w-4 mr-1" />
                Share
              </Button>
              {onEdit && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onEdit}
                >
                  <Edit className="h-4 w-4 mr-1" />
                  Edit
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Fullscreen Modal */}
      <Dialog open={isFullscreen} onOpenChange={setIsFullscreen}>
        <DialogContent className="max-w-6xl w-full h-[90vh]">
          <DialogHeader>
            <DialogTitle className="capitalize">{type} Viewer</DialogTitle>
          </DialogHeader>
          <div className="flex-1 flex items-center justify-center">
            {type === 'video' && (
              <video
                src={url}
                controls
                className="max-w-full max-h-full"
                autoPlay={isPlaying}
              />
            )}
            {type === 'image' && (
              <img
                src={url}
                alt="Full size"
                className="max-w-full max-h-full object-contain"
              />
            )}
            {type === 'audio' && (
              <div className="w-full max-w-2xl">
                {renderAudioPlayer()}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};