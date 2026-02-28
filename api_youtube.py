import os
import re
from datetime import datetime, timezone, timedelta
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

class YouTubeAgent:
    def __init__(self):
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            print("[경고] .env 파일에 YOUTUBE_API_KEY가 없습니다.")
        
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.formatter = TextFormatter()

    def _parse_duration_to_seconds(self, duration_str):
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if not match:
            return 0
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds

    def _is_live_or_continuous_stream(self, video_item):
        snippet = video_item.get('snippet', {})
        
        live_content = snippet.get('liveBroadcastContent', 'none')
        if live_content in ['live', 'upcoming']:
            return True
            
        title = snippet.get('title', '').upper()
        if '[LIVE]' in title or '라이브' in title or '실시간' in title or '[이슈PLAY]' in title:
            return True
            
        return False

    def fill_missing_ids(self, config_data):
        updated = False
        for row in config_data:
            handle = row.get('Handle', '')
            channel_id = row.get('ChannelID', '')
            
            if handle and not channel_id:
                try:
                    response = self.youtube.search().list(
                        part='snippet',
                        q=handle,
                        type='channel',
                        maxResults=1
                    ).execute()
                    
                    if response.get('items'):
                        found_id = response['items'][0]['id']['channelId']
                        uploads_id = found_id.replace('UC', 'UU')
                        
                        row['ChannelID'] = found_id
                        row['UploadsID'] = uploads_id
                        updated = True
                        print(f"[설정 업데이트] {handle} -> {found_id}")
                except Exception as e:
                    print(f"[검색 에러] {handle}: {str(e)}")
                    
        return updated

    def fetch_videos(self, config_data):
        results = []
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=1)
        
        for row in config_data:
            category = row.get('Category')
            channel = row.get('Handle')
            criteria = row.get('FilterCriteria', '').lower()
            target_playlist = row.get('TargetPlaylistID')
            uploads_id = row.get('UploadsID')
            
            playlist_id = target_playlist if target_playlist else uploads_id
            if not playlist_id:
                continue
                
            try:
                if 'newest' in criteria:
                    video = self._fetch_newest(playlist_id, cutoff_time)
                    if video:
                        self._append_video_info(results, video, category, channel)
                
                elif 'most viewed' in criteria:
                    video = self._fetch_most_viewed(playlist_id, cutoff_time)
                    if video:
                        self._append_video_info(results, video, category, channel)
                        
            except Exception as e:
                print(f"[수집 에러] {channel}: {str(e)}")
                
        return results

    def _fetch_newest(self, playlist_id, cutoff_time):
        response = self.youtube.playlistItems().list(
            part='contentDetails',
            playlistId=playlist_id,
            maxResults=10
        ).execute()
        
        items = response.get('items', [])
        if not items:
            return None
            
        video_ids = [item['contentDetails']['videoId'] for item in items]
        
        video_response = self.youtube.videos().list(
            part='snippet,contentDetails',
            id=','.join(video_ids)
        ).execute()
        
        for v in video_response.get('items', []):
            if self._is_live_or_continuous_stream(v):
                continue
                
            pub_str = v['snippet']['publishedAt']
            pub_time = datetime.fromisoformat(pub_str.replace('Z', '+00:00'))
            
            duration_str = v['contentDetails']['duration']
            duration_sec = self._parse_duration_to_seconds(duration_str)
            
            if pub_time >= cutoff_time and duration_sec <= 3600:
                return v
                
        return None

    def _fetch_most_viewed(self, playlist_id, cutoff_time):
        list_response = self.youtube.playlistItems().list(
            part='contentDetails',
            playlistId=playlist_id,
            maxResults=15
        ).execute()
        
        video_ids = [item['contentDetails']['videoId'] for item in list_response.get('items', [])]
        if not video_ids:
            return None
            
        video_response = self.youtube.videos().list(
            part='snippet,statistics,contentDetails',
            id=','.join(video_ids)
        ).execute()
        
        recent_videos = []
        for v in video_response.get('items', []):
            if self._is_live_or_continuous_stream(v):
                continue
                
            pub_str = v['snippet']['publishedAt']
            pub_time = datetime.fromisoformat(pub_str.replace('Z', '+00:00'))
            
            duration_str = v['contentDetails']['duration']
            duration_sec = self._parse_duration_to_seconds(duration_str)
            
            if pub_time >= cutoff_time and duration_sec <= 3600:
                recent_videos.append(v)
                
        if recent_videos:
            recent_videos.sort(key=lambda x: int(x['statistics']['viewCount']), reverse=True)
            return recent_videos[0]
            
        return None

    def _append_video_info(self, results, video_item, category, channel):
        snippet = video_item['snippet']
        
        if 'contentDetails' in video_item and 'videoId' in video_item['contentDetails']:
            video_id = video_item['contentDetails']['videoId']
        else:
            video_id = video_item['id']
            
        thumbnail = snippet['thumbnails'].get('high', snippet['thumbnails'].get('default'))
        thumbnail_url = thumbnail['url'] if thumbnail else ''
        
        results.append({
            'category': category,
            'channel': channel,
            'title': snippet['title'],
            'videoId': video_id,
            'description': snippet['description'][:500],
            'publishedAt': snippet['publishedAt'],
            'thumbnailUrl': thumbnail_url
        })

    def extract_transcript(self, video_id):
        try:
            ytt_api = YouTubeTranscriptApi()
            transcript_data = ytt_api.fetch(video_id, languages=['ko', 'en'])
            
            text_formatted = self.formatter.format_transcript(transcript_data)
            print(f"  [자막 확보 완료] {video_id}")
            return text_formatted
        except Exception as e:
            print(f"  [자막 없음/추출 실패] {video_id}: {str(e)}")
            return None