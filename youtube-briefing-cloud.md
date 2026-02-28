# Youtube Briefing Cloud

## Workflow Files List

- 0-common-helpers.gs
- 1-setup.gs
- 2-youtube-api.gs
- 3-gemini-ai.gs
- 4-storage-publish.gs
- main.gs

## Test

```jsx
/**
 * 외부 네트워크 통신 및 스크립트 속성(API Key) 테스트
 */
function checkNetworkAndProperties() {
  const props = PropertiesService.getScriptProperties();
  const geminiKey = props.getProperty('GEMINI_API_KEY');
  const youtubeKey = props.getProperty('YOUTUBE_API_KEY');
  
  // 1. 스크립트 속성 확인
  if (!geminiKey || !youtubeKey) {
    console.warn('❌ 경고: 스크립트 속성에 API 키가 설정되지 않았습니다.');
    return;
  }
  
  // 2. 외부 URL 호출 테스트 (Google 메인 페이지)
  try {
    const response = UrlFetchApp.fetch('https://www.google.com', { muteHttpExceptions: true });
    if (response.getResponseCode() === 200) {
      console.log('✅ 확인 완료: 외부 네트워크(UrlFetchApp) 통신이 정상입니다.');
    }
  } catch (e) {
    console.error('❌ 오류: 외부 통신이 차단되었습니다: ' + e.toString());
  }
}
```

```jsx
/**
 * Blogger API 및 이미지 렌더링 테스트 (UrlFetchApp 직접 호출 버전)
 */
function checkBloggerService() {
  const blogId = '5076676446040183000'; // 사용자 지정 Blog ID
  
  // 테스트용 YouTube Thumbnail(썸네일) URL
  const testThumbnail = 'https://img.youtube.com/vi/0lHFniBCuJw/maxresdefault.jpg';
  
  const htmlContent = '<h2>시스템 연동 테스트</h2>' +
                    '<p>이 포스트가 보인다면 UrlFetchApp을 통한 직접 호출에 성공한 것입니다.</p>' +
                    '<img src="' + testThumbnail + '" style="max-width:100%; border-radius:10px;"/>' +
                    '<p>위의 이미지가 정상적으로 보인다면 YouTube 호스팅 자산을 직접 활용할 수 있습니다.</p>';
  
  // REST API 엔드포인트 및 Draft(초안) 옵션 설정
  const url = 'https://www.googleapis.com/blogger/v3/blogs/' + blogId + '/posts?isDraft=true';
  
  const payload = {
    kind: 'blogger#post',
    title: '🛠 실습 사전 점검 포스트 (UrlFetchApp 버전)',
    content: htmlContent
  };
  
  const options = {
    method: 'post',
    contentType: 'application/json',
    headers: {
      Authorization: 'Bearer ' + ScriptApp.getOAuthToken() // 매니페스트에 정의된 권한 토큰 사용
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };
  
  try {
    const response = UrlFetchApp.fetch(url, options);
    const responseCode = response.getResponseCode();
    const result = JSON.parse(response.getContentText());
    
    if (responseCode === 200 || responseCode === 201) {
      console.log('확인 완료: Blogger 초안 게시물이 성공적으로 생성되었습니다.');
      console.log('확인용 URL: ' + result.url);
    } else {
      console.error('오류 발생: HTTP ' + responseCode);
      console.error('응답 본문: ' + response.getContentText());
    }
  } catch (e) {
    console.error('네트워크 또는 권한 오류: ' + e.toString());
  }
}
```

## Workflow Files

### 0-common-helpers.gs

```jsx
// ─── Google Drive 폴더 기반 Sheets 접근 헬퍼 ────────
var FOLDER_NAME = 'Google Blogger';

function getBloggerFolder() {
  var folders = DriveApp.getFoldersByName(FOLDER_NAME);
  if (!folders.hasNext()) {
    throw new Error('"' + FOLDER_NAME + '" 폴더가 없습니다. Google Drive에 먼저 생성해주세요.');
  }
  return folders.next();
}

function getConfigSheet() {
  var folder = getBloggerFolder();
  var files = folder.getFilesByName('Config');
  if (!files.hasNext()) {
    throw new Error('"' + FOLDER_NAME + '" 폴더에 "Config" 스프레드시트가 없습니다.');
  }
  return SpreadsheetApp.open(files.next()).getSheets()[0];
}

function getMonthlySpreadsheet() {
  var folder = getBloggerFolder();
  var name = 'blogger-'
    + Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM');

  var files = folder.getFilesByName(name);
  if (files.hasNext()) {
    return SpreadsheetApp.open(files.next());
  }

  // 새 월간 스프레드시트 자동 생성
  var ss = SpreadsheetApp.create(name);
  var file = DriveApp.getFileById(ss.getId());
  folder.addFile(file);
  DriveApp.getRootFolder().removeFile(file);

  // detail 탭 (기본 Sheet1 → 이름 변경 + 헤더)
  var detail = ss.getSheets()[0];
  detail.setName('detail');
  detail.appendRow([
    'date','category','channel','title','core_fact',
    'actionable_insight','noise_analysis','score','grade',
    'signal_ratio','reasoning','thumbnailUrl','videoUrl'
  ]);

  // daily 탭 생성 + 헤더
  var daily = ss.insertSheet('daily');
  daily.appendRow([
    'date','investment','affairs','science','insight','htmlBody'
  ]);

  return ss;
}

/**
 * YouTube Data API v3 호출을 위한 공통 헬퍼 함수
 * 모든 YouTube API 요청을 일관되게 처리하기 위한 내부 함수입니다.
 * @param {string} endpoint - API 엔드포인트 (예: 'playlistItems')
 * @param {Object} params - 쿼리 파라미터 객체
 * @returns {Object} JSON 응답 데이터
 */
const callYouTubeAPI = (endpoint, params) => {
  const apiKey = PropertiesService.getScriptProperties().getProperty('YOUTUBE_API_KEY');
  const queryString = Object.keys(params)
    .map(k => `${encodeURIComponent(k)}=${encodeURIComponent(params[k])}`)
    .join('&');
  
  const url = `https://www.googleapis.com/youtube/v3/${endpoint}?${queryString}&key=${apiKey}`;
  const response = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  
  if (response.getResponseCode() !== 200) {
    throw new Error(`YouTube API 오류: ${response.getContentText()}`);
  }
  
  return JSON.parse(response.getContentText());
};

// 이미 처리되어 detail 시트에 기록된 Video ID 목록을 가져옵니다.
function getProcessedVideoIds() {
  const spreadsheet = getMonthlySpreadsheet();
  const sheet = spreadsheet.getSheetByName('detail');
  
  if (!sheet) {
    console.log('detail 시트가 없어 중복 검사를 건너뜁니다.');
    return [];
  }
  
  const data = sheet.getDataRange().getValues();
  const processedIds = [];
  
  // 첫 번째 행(헤더)을 제외하고 전체 데이터 순회
  for (let i = 1; i < data.length; i++) {
    // 열 위치에 의존하지 않고 행 전체를 하나의 문자열로 병합
    const rowString = data[i].join(' '); 
    // v= 뒤에 붙는 11자리 YouTube 고유 식별자 정규식 추출
    const match = rowString.match(/v=([a-zA-Z0-9_-]{11})/); 
    
    if (match) {
      processedIds.push(match[1]);
    }
  }
  
  console.log('기존 처리된 영상 ID ' + processedIds.length + '개를 확인했습니다.');
  return processedIds;
}

// 자막 스크립트 추출 헬퍼 (안드로이드 모바일 클라이언트 위장 방식)
function getTranscripts(videoData) {
  console.log('자막 추출을 시작합니다 (안드로이드 모바일 클라이언트 우회).');
  
  const apiUrl = 'https://www.youtube.com/youtubei/v1/player?key=AIzaSyAO_FWF7wTFOuQ6zQ-K_T8bF2_45Jb0e-E';
  
  const apiRequests = videoData.map(v => ({
    url: apiUrl,
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify({
      context: {
        client: {
          hl: 'ko',
          gl: 'KR',
          clientName: 'ANDROID',
          clientVersion: '17.31.35',
          androidSdkVersion: 31,
          userAgent: 'com.google.android.youtube/17.31.35 (Linux; U; Android 12; ko_KR)'
        }
      },
      videoId: v.videoId
    }),
    muteHttpExceptions: true
  }));
  
  const apiResponses = UrlFetchApp.fetchAll(apiRequests);
  const captionRequests = [];
  const captionMap = {};
  
  apiResponses.forEach((res, i) => {
    try {
      const json = JSON.parse(res.getContentText());
      const videoTitle = videoData[i].title;
      
      if (json.playabilityStatus && json.playabilityStatus.status === 'ERROR') {
         console.log('[접근 불가] ' + videoTitle + ' - ' + json.playabilityStatus.reason);
         return;
      }

      if (json.captions && json.captions.playerCaptionsTracklistRenderer) {
        const tracks = json.captions.playerCaptionsTracklistRenderer.captionTracks;
        const targetTrack = tracks.find(t => t.languageCode.includes('ko')) || tracks[0];
        
        if (targetTrack) {
          captionMap[captionRequests.length] = i;
          captionRequests.push({
            url: targetTrack.baseUrl,
            muteHttpExceptions: true
          });
          console.log('[자막 확보 성공] ' + videoTitle);
        }
      } else {
        console.log('[자막 노드 누락] ' + videoTitle + ' - 모바일 응답에도 자막이 포함되지 않았습니다.');
      }
    } catch (e) {
      console.error('[API 응답 파싱 실패] ' + videoData[i].title + ': ' + e.message);
    }
  });
  
  if (captionRequests.length === 0) {
    console.log('추출 가능한 자막이 없습니다. 영상 설명(Description) 기반으로 폴백 분석을 진행합니다.');
    return {};
  }
  
  const captions = UrlFetchApp.fetchAll(captionRequests);
  const transcripts = {};
  const MIN_TRANSCRIPT_LENGTH = 50; 
  
  captions.forEach((res, idx) => {
    try {
      const xml = res.getContentText();
      const text = xml
        .replace(/<[^>]+>/g, ' ')
        .replace(/&#39;/g, "'")
        .replace(/&amp;/g, '&')
        .replace(/&quot;/g, '"')
        .replace(/\s+/g, ' ')
        .trim();
        
      const originalIndex = captionMap[idx];
      if (text.length >= MIN_TRANSCRIPT_LENGTH) {
        transcripts[originalIndex] = text;
      }
    } catch (e) {
      console.error('자막 텍스트 변환 실패: ' + e.message);
    }
  });
  
  return transcripts;
}
```

### 1-setup.gs

```jsx
/**
 * Phase 1: 채널 핸들을 기반으로 ChannelID와 UploadsID(UU...) 자동 설정
 */
function setupChannelIds() {
  const sheet = getConfigSheet(); // Config 시트 접근
  const data = sheet.getDataRange().getValues();
  const youtubeKey = PropertiesService.getScriptProperties().getProperty('YOUTUBE_API_KEY');

  for (let i = 1; i < data.length; i++) {
    const handle = data[i][1]; // Column B: Handle (@MK_Invest 등)
    
    // ChannelID(Column E)가 비어있는 경우에만 실행
    if (handle && !data[i][4]) { 
      try {
        // search.list API 호출 (100 유닛 소모, 최초 1회만 사용)
        const url = `https://www.googleapis.com/youtube/v3/search?part=snippet&q=${encodeURIComponent(handle)}&type=channel&maxResults=1&key=${youtubeKey}`;
        const response = UrlFetchApp.fetch(url);
        const json = JSON.parse(response.getContentText());

        if (json.items && json.items.length > 0) {
          const channelId = json.items[0].id.channelId;
          const uploadsId = channelId.replace('UC', 'UU'); // UC -> UU 변환 기법 적용

          sheet.getRange(i + 1, 5).setValue(channelId);  // Column E: ChannelID
          sheet.getRange(i + 1, 6).setValue(uploadsId);  // Column F: UploadsID
          
          console.log(`✅ ${handle} 설정 완료: ${channelId}`);
        }
      } catch (e) {
        console.error(`❌ ${handle} 검색 실패: ${e.toString()}`);
      }
      
      // API 할당량 보호를 위해 짧은 지연 (선택 사항)
      Utilities.sleep(200);
    }
  }
}
```

### 2-youtube-api.gs

```jsx

/**
 * 2-1. 최신 영상 수집 (Newest)
 * 각 채널의 '전체 업로드(UU...)' 또는 지정된 플레이리스트에서 가장 최근 영상 1개를 가져옵니다
 * 할당량 효율: 채널당 1 유닛 소모
 */
function fetchNewestVideos() {
  console.log('--- 📡 [Newest] 수집 시작 ---');
  const config = getConfigSheet().getDataRange().getValues();
  const results = [];
  const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000);

  for (let i = 1; i < config.length; i++) {
    const [category, channel, criteria, targetPlaylistId, , uploadsId] = config[i];
    const playlistId = targetPlaylistId || uploadsId;

    if (criteria.includes('newest')) {
      try {
        const res = callYouTubeAPI('playlistItems', {
          part: 'snippet,contentDetails',
          playlistId: playlistId,
          maxResults: 1
        });

        if (res.items && res.items.length > 0) {
          const item = res.items[0].snippet;
          const publishedAt = new Date(item.publishedAt);

          if (publishedAt >= cutoff) {
            console.log(`✅ [신호 발견] ${channel}: ${item.title} (${item.publishedAt})`); //
            results.push({
              category, channel, title: item.title,
              videoId: res.items[0].contentDetails.videoId,
              description: item.description.substring(0, 500),
              publishedAt: item.publishedAt,
              thumbnailUrl: item.thumbnails.high ? item.thumbnails.high.url : item.thumbnails.default.url
            });
          } else {
            console.log(`⏭️ [오래된 영상] ${channel}: 24시간 이내의 영상이 아닙니다.`); //
          }
        }
      } catch (e) {
        console.error(`❌ [${channel}] 에러: ${e.message}`);
      }
    }
  }
  console.log(`📊 [Newest] 완료: 총 ${results.length}개 수집`);
  return results;
}

/**
 * 2-2. 최고 조회수 수집 (Most Viewed)
 * 최근 10개 영상 중 24시간 이내 발행되었으며 조회수가 가장 높은 영상을 선별
 * 할당량 효율: 채널당 약 2 유닛 소모
 */
function fetchMostViewedVideos() {
  console.log('--- 📈 [Most Viewed] 수집 시작 ---');
  const config = getConfigSheet().getDataRange().getValues();
  const results = [];
  const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000);

  for (let i = 1; i < config.length; i++) {
    const [category, channel, criteria, , , uploadsId] = config[i];

    if (criteria.includes('most viewed')) {
      try {
        const listRes = callYouTubeAPI('playlistItems', {
          part: 'contentDetails', playlistId: uploadsId, maxResults: 10
        });

        const videoIds = listRes.items.map(item => item.contentDetails.videoId);
        if (videoIds.length === 0) continue;

        const videoRes = callYouTubeAPI('videos', {
          part: 'snippet,statistics', id: videoIds.join(',')
        });

        const recentVideos = videoRes.items.filter(v => new Date(v.snippet.publishedAt) >= cutoff);
        console.log(`🔍 [${channel}] 24시간 이내 영상 ${recentVideos.length}개 발견 (조회수 비교 중...)`); //

        const topVideo = recentVideos.sort((a, b) => parseInt(b.statistics.viewCount) - parseInt(a.statistics.viewCount))[0];

        if (topVideo) {
          console.log(`🔥 [최고 조회수 선택] ${channel}: ${topVideo.snippet.title} (조회수: ${topVideo.statistics.viewCount})`);
          results.push({
            category, channel, title: topVideo.snippet.title, videoId: topVideo.id,
            description: topVideo.snippet.description.substring(0, 500),
            publishedAt: topVideo.snippet.publishedAt, viewCount: topVideo.statistics.viewCount,
            thumbnailUrl: topVideo.snippet.thumbnails.high ? topVideo.snippet.thumbnails.high.url : topVideo.snippet.thumbnails.default.url
          });
        }
      } catch (e) {
        console.error(`❌ [${channel}] 에러: ${e.message}`);
      }
    }
  }
  console.log(`📊 [Most Viewed] 완료: 총 ${results.length}개 수집`);
  return results;
}

```

### 3-gemini-ai.gs

```jsx

// 카테고리별 조건부 시스템 명령어 설정
function getSystemInstruction(category) {
  const base = '당신은 Information Theory 관점의 미디어 분석가입니다. '
    + '텍스트에서 신호(Signal)와 소음(Noise)을 분리하여 정량화하는 것이 임무입니다. '
    + '주관적 해석을 배제하고, 아래 정의에 따라 엄격하게 분류하십시오.\n\n';

  const categoryRules = {
    'Investment': '■ 신호(Signal) 정의:\n'
      + '- 거시 경제 지표(GDP, CPI, 금리, 환율 등)의 구체적 수치 변화\n'
      + '- 자산 가격(주가, 원자재, 채권 등)의 명확한 방향성과 변동폭\n'
      + '- 기업 실적, 정책 결정 등 검증 가능한 팩트\n\n'
      + '■ 소음(Noise) 정의:\n'
      + '- "오를 수도 있고 내릴 수도 있다" 식의 무가치 전망 -> 라벨: tautology\n'
      + '- "폭락", "대폭등", "공포" 등 자극적 수식어 -> 라벨: fear_greed\n'
      + '- 근거 없는 목표가, 확증 편향적 낙관/비관 -> 라벨: ungrounded_prediction\n'
      + '- 광고성 종목 추천, 리딩방 유도 -> 라벨: promotion',
    'Affairs': '■ 신호(Signal) 정의:\n'
      + '- 법안·제도 변화의 구체적 내용과 시행 일정\n'
      + '- 지정학적 분쟁·외교 사건의 사실관계 (누가, 언제, 무엇을)\n'
      + '- 공식 발표, 통계, 판결문 등 검증 가능한 1차 출처\n\n'
      + '■ 소음(Noise) 정의:\n'
      + '- 특정 정치 진영의 편향된 프레이밍 -> 라벨: political_bias\n'
      + '- 사실 전달이 아닌 가치 판단·도덕적 훈계 -> 라벨: value_judgment\n'
      + '- 본질과 무관한 인신공격, 조롱, 비아냥 -> 라벨: ad_hominem\n'
      + '- 감정적 호소, 분노 유발 수사법 -> 라벨: emotional_appeal',
    'Popular Science': '■ 신호(Signal) 정의:\n'
      + '- 기술·현상의 핵심 작동 메커니즘에 대한 정확한 설명\n'
      + '- 기존 한계 돌파 여부, 벤치마크 수치, 실험 결과\n'
      + '- 실용적 적용 가능성과 구체적 타임라인\n\n'
      + '■ 소음(Noise) 정의:\n'
      + '- 실현 가능성이 입증되지 않은 과장된 기대감 -> 라벨: hype\n'
      + '- 설명에 기여하지 않는 학술 용어 나열 -> 라벨: jargon_overload\n'
      + '- "혁명적", "게임체인저" 등 내용 없는 수식어 -> 라벨: empty_modifier\n'
      + '- SF적 상상을 사실처럼 서술 -> 라벨: speculation'
  };

  return base + (categoryRules[category] || categoryRules['Affairs']);
}

// 4차원 제이슨 스키마 정의
function getAnalysisSchema() {
  return {
    type: 'OBJECT',
    properties: {
      core_fact: {
        type: 'ARRAY',
        description: '구체적 수치와 명확한 방향성을 지닌 객관적 사실.',
        items: { type: 'STRING' }
      },
      actionable_insight: {
        type: 'ARRAY',
        description: 'core_fact에 기반한 논리적 추론 및 시사점.',
        items: { type: 'STRING' }
      },
      noise_analysis: {
        type: 'ARRAY',
        description: '정보가 없는 발언의 추출과 라벨링.',
        items: {
          type: 'OBJECT',
          properties: {
            quote: { type: 'STRING', description: '원문에서 추출한 소음 발언 (직접 인용)' },
            label: { type: 'STRING', description: '소음 유형 라벨' }
          },
          required: ['quote', 'label']
        }
      },
      information_value: {
        type: 'OBJECT',
        description: '전체 텍스트의 신호 대 소음 비율 평가.',
        properties: {
          score: { type: 'INTEGER', description: '정보 가치 점수 (0-100)' },
          grade: { type: 'STRING', enum: ['A','B','C','D','F'], description: '등급' },
          signal_ratio: { type: 'STRING', description: '신호 비율 (예: "72%")' },
          reasoning: { type: 'STRING', description: '평가 근거 1줄 요약' }
        },
        required: ['score', 'grade', 'signal_ratio', 'reasoning']
      }
    },
    required: ['core_fact', 'actionable_insight', 'noise_analysis', 'information_value']
  };
}

// 요청 제한 방어적 청크 병렬 처리 헬퍼
function fetchAllChunked(requests, chunkSize, delayMs) {
  let allResponses = [];
  for (let i = 0; i < requests.length; i += chunkSize) {
    const chunk = requests.slice(i, i + chunkSize);
    console.log('Gemini API 호출 중... (' + (i + 1) + ' ~ ' + Math.min(i + chunkSize, requests.length) + ' / ' + requests.length + ')');
    
    const responses = UrlFetchApp.fetchAll(chunk);
    allResponses = allResponses.concat(responses);
    
    if (i + chunkSize < requests.length) {
      Utilities.sleep(delayMs);
    }
  }
  return allResponses;
}

// 영상 분석 메인 함수
const GEMINI_CHUNK_SIZE = 4;
const GEMINI_CHUNK_DELAY = 2000;

function analyzeWithGemini(videoData) {
  if (!videoData || videoData.length === 0) return [];
  
  const API_KEY = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  const ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key=' + API_KEY;
  const responseSchema = getAnalysisSchema();
  const transcripts = getTranscripts(videoData);

  const requests = videoData.map((v, i) => {
    const script = transcripts[i];
    const systemText = getSystemInstruction(v.category);
    let userText = '아래 영상 텍스트에서 신호와 소음을 분리 분석하십시오.\n\n제목: ' + v.title + '\n채널: ' + v.channel + '\n';
    
    if (script) {
      userText += '\n[전체 자막 스크립트]\n' + script.substring(0, 30000);
    } else {
      userText += '\n[영상 설명]\n' + v.description;
    }
    
    return {
      url: ENDPOINT,
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify({
        system_instruction: { parts: [{ text: systemText }] },
        contents: [{ parts: [{ text: userText }] }],
        generationConfig: { responseMimeType: 'application/json', responseSchema: responseSchema }
      }),
      muteHttpExceptions: true
    };
  });

  const responses = fetchAllChunked(requests, GEMINI_CHUNK_SIZE, GEMINI_CHUNK_DELAY);
  const results = [];
  
  responses.forEach((res, i) => {
    try {
      const json = JSON.parse(res.getContentText());
      
      if (json.error) {
        console.error('Gemini API 오류 (' + videoData[i].title + '): ' + json.error.message);
        return;
      }
      
      if (!json.candidates || json.candidates.length === 0 || !json.candidates[0].content) {
        console.error('Gemini API 응답 구조 오류 또는 안전 필터 차단 (' + videoData[i].title + ')');
        return;
      }
      
      let textResponse = json.candidates[0].content.parts[0].text;
      textResponse = textResponse.replace(/^```json\s*/i, '').replace(/\s*```$/i, '');
      const result = JSON.parse(textResponse);
      
      console.log('분석 완료: [' + result.information_value.grade + '] ' + videoData[i].title);
      
      results.push({
        videoId: videoData[i].videoId,
        channel: videoData[i].channel,
        title: videoData[i].title,
        category: videoData[i].category,
        core_fact: result.core_fact,
        actionable_insight: result.actionable_insight,
        noise_analysis: result.noise_analysis,
        information_value: result.information_value,
        thumbnailUrl: videoData[i].thumbnailUrl
      });
    } catch (e) {
      console.error('분석 결과 파싱 실패 (' + videoData[i].title + '): ' + e.message);
    }
  });
  
  return results;
}

// 통합 브리핑 작성 함수
function generateDailyBriefing(summaries) {
  console.log('통합 브리핑 생성을 시작합니다.');
  const API_KEY = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  const ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key=' + API_KEY;

  const responseSchema = {
    type: 'OBJECT',
    properties: {
      investment: { type: 'STRING', description: '투자 카테고리 핵심 요약' },
      affairs:    { type: 'STRING', description: '시사 카테고리 핵심 요약' },
      science:    { type: 'STRING', description: '과학 카테고리 핵심 요약' },
      insight:    { type: 'STRING', description: '오늘의 투자 시사점' },
      htmlBody:   { type: 'STRING', description: 'Blogger 게시용 HTML 본문' }
    },
    required: ['investment', 'affairs', 'science', 'insight', 'htmlBody']
  };

  const res = UrlFetchApp.fetch(ENDPOINT, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify({
      contents: [{ parts: [{ text: '아래 영상 요약을 바탕으로 "오늘의 경제 브리핑"을 작성해줘.\n'
        + '카테고리별 핵심 3줄 + 투자 시사점 1줄 + Blogger HTML 본문.\n\n'
        + JSON.stringify(summaries) }] }],
      generationConfig: { responseMimeType: 'application/json', responseSchema: responseSchema }
    }),
    muteHttpExceptions: true
  });

  const json = JSON.parse(res.getContentText());
  
  if (json.error) {
    throw new Error('브리핑 생성 실패: ' + json.error.message);
  }
  
  if (!json.candidates || json.candidates.length === 0 || !json.candidates[0].content) {
    throw new Error('브리핑 응답 구조 오류 또는 안전 필터에 의해 차단되었습니다.');
  }
  
  let textResponse = json.candidates[0].content.parts[0].text;
  textResponse = textResponse.replace(/^```json\s*/i, '').replace(/\s*```$/i, '');
  
  console.log('통합 브리핑 생성이 완료되었습니다.');
  return JSON.parse(textResponse);
}
```

### 4-storage-publish.gs

```jsx
// 구글 시트 상세 분석 저장
function saveDetailAnalyses(analyses) {
  const sheet = getMonthlySpreadsheet().getSheetByName('detail');
  const today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd');

  analyses.forEach(a => {
    sheet.appendRow([
      today, a.category, a.channel, a.title,
      JSON.stringify(a.core_fact), JSON.stringify(a.actionable_insight),
      JSON.stringify(a.noise_analysis), a.information_value.score,
      a.information_value.grade, a.information_value.signal_ratio,
      a.information_value.reasoning,
      `=IMAGE("${a.thumbnailUrl}")`,
      'https://youtube.com/watch?v=' + a.videoId
    ]);
  });
}

// 구글 시트 통합 브리핑 저장
function saveDailyBriefing(briefing) {
  const sheet = getMonthlySpreadsheet().getSheetByName('daily');
  const today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd');

  sheet.appendRow([
    today, briefing.investment, briefing.affairs,
    briefing.science, briefing.insight, briefing.htmlBody
  ]);
}

// 지수 백오프가 적용된 API 호출 헬퍼
function fetchWithBackoff(url, options, maxRetries = 3) {
  let retries = 0;
  let delay = 5000; // 초기 대기 시간을 5초로 넉넉하게 설정

  while (retries <= maxRetries) {
    const response = UrlFetchApp.fetch(url, options);
    const code = response.getResponseCode();

    if (code === 200 || code === 201) {
      return response;
    } else if (code === 429 || code >= 500) {
      if (retries === maxRetries) {
        console.error('최대 재시도 초과. API 응답: ' + response.getContentText());
        return response;
      }
      console.log('HTTP ' + code + ' 감지. ' + (delay / 1000) + '초 후 재시도합니다.');
      Utilities.sleep(delay);
      retries++;
      delay = delay * 2; // 대기 시간 2배씩 증가
    } else {
      console.error('복구할 수 없는 오류: ' + response.getContentText());
      return response;
    }
  }
}

// 블로거 개별 영상 포스트 게시
function publishVideoPost(analysis) {
  const blogId = '5076676446040183000';
  
  const coreFacts = analysis.core_fact || [];
  const insights = analysis.actionable_insight || [];
  const infoValue = analysis.information_value || {};
  
  const htmlContent = '<div style="text-align:center;margin-bottom:20px;">'
    + '<img src="' + analysis.thumbnailUrl + '" alt="thumbnail"'
    + ' style="max-width:100%;border-radius:8px;"/></div>'
    + '<h3>핵심 사실 (Core Facts)</h3><ul>'
    + coreFacts.map(f => '<li>' + f + '</li>').join('')
    + '</ul><h3>시사점 (Actionable Insights)</h3><ul>'
    + insights.map(i => '<li>' + i + '</li>').join('')
    + '</ul><h3>정보 가치 평가 (Evaluation)</h3>'
    + '<p>' + (infoValue.grade || 'N/A') + ' ('
    + (infoValue.score || 0) + '/100) | 신호 비율: '
    + (infoValue.signal_ratio || 'N/A') + '</p>'
    + '<p>' + (infoValue.reasoning || '') + '</p>'
    + '<p><a href="https://youtube.com/watch?v=' + analysis.videoId + '">원본 영상 보기</a></p>';

  const payload = {
    kind: 'blogger#post',
    blog: { id: blogId },
    title: analysis.title,
    content: htmlContent,
    labels: [analysis.category]
  };

  const url = 'https://www.googleapis.com/blogger/v3/blogs/' + blogId + '/posts';
  
  fetchWithBackoff(url, {
    method: 'post',
    contentType: 'application/json',
    headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
}

// 블로거 통합 브리핑 포스트 게시
function publishBriefingPost(briefingHtml, analyses, categories) {
  const blogId = '5076676446040183000';
  const today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd');
  
  let gallery = '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;">';
  analyses.forEach(a => {
    gallery += '<a href="https://youtube.com/watch?v=' + a.videoId + '">'
      + '<img src="' + a.thumbnailUrl + '" alt="thumbnail"'
      + ' style="width:180px;border-radius:6px;"/></a>';
  });
  gallery += '</div>';

  const payload = {
    kind: 'blogger#post',
    blog: { id: blogId },
    title: today + ' 뉴스 브리핑',
    content: gallery + (briefingHtml || ''),
    labels: categories || []
  };

  const url = 'https://www.googleapis.com/blogger/v3/blogs/' + blogId + '/posts';
  
  fetchWithBackoff(url, {
    method: 'post',
    contentType: 'application/json',
    headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
}
```

### main.gs

```jsx
// 전체 시스템 오케스트레이터: Main.gs
function runDailyPipeline() {
  console.log('데일리 파이프라인 시작');

  // Phase 2 데이터 수집
  const newestVideos = fetchNewestVideos();
  const mostViewedVideos = fetchMostViewedVideos();
  const allVideos = [...newestVideos, ...mostViewedVideos];

  if (allVideos.length === 0) {
    console.log('24시간 이내의 새로운 영상 신호가 없습니다. 종료합니다.');
    return;
  }

  // 중복 방지: 이미 처리된 영상 필터링
  const processedIds = getProcessedVideoIds();
  const newVideosToProcess = allVideos.filter(v => !processedIds.includes(v.videoId));
  
  if (newVideosToProcess.length === 0) {
    console.log('수집된 영상 ' + allVideos.length + '개가 모두 이미 처리되었습니다. 종료합니다.');
    return; // 중복 실행 시 여기서 안전하게 차단됨
  }
  
  console.log('중복 제외 완료: 총 ' + newVideosToProcess.length + '개의 새로운 영상을 분석합니다.');

  // Phase 3-1 데이터 개별 분석
  console.log('Gemini Flash-Lite 1차 분석을 시작합니다.');
  const analyzedData = analyzeWithGemini(allVideos);

  if (analyzedData.length === 0) {
    console.error('분석된 데이터가 없습니다. 파이프라인을 종료합니다.');
    return;
  }
  console.log('1차 분석 완료: ' + analyzedData.length + '개 영상 처리됨.');
  
  // Phase 3-2 통합 브리핑 생성
  // console.log('Gemini Pro 통합 브리핑 생성을 시작합니다.');
  // let briefingData = null;
  // try {
  //   briefingData = generateDailyBriefing(analyzedData);
  //   console.log('2차 통합 브리핑 완료.');
  // } catch (e) {
  //   console.error('통합 브리핑 생성 중 오류 발생: ' + e.message);
  // }

  // Phase 4 저장 및 발행
  console.log('구글 시트 기록을 시작합니다.');
  saveDetailAnalyses(analyzedData);
  
  if (briefingData) {
    saveDailyBriefing(briefingData);
  }
  
  console.log('블로거 게시물 생성을 시작합니다.');
  analyzedData.forEach((a, idx) => {
    publishVideoPost(a);
    if (idx < analyzedData.length - 1) Utilities.sleep(10000); 
  });
  
  // if (briefingData) {
  //   const categories = Object.keys(analyzedData.reduce((acc, a) => { acc[a.category] = true; return acc; }, {}));
  //   publishBriefingPost(briefingData.htmlBody, analyzedData, categories);
  // }
  
  console.log('전체 프로세스 완료.');
}
```
