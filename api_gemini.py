import os
import json
import google.generativeai as genai

class GeminiAnalyzer:
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("[경고] .env 파일에 GEMINI_API_KEY가 없습니다.")
        genai.configure(api_key=api_key)

    def _get_system_instruction(self, category):
        base = (
            "당신은 Information Theory 관점의 미디어 분석가입니다. "
            "텍스트에서 신호(Signal)와 소음(Noise)을 분리하여 정량화하는 것이 임무입니다. "
            "주관적 해석을 배제하고, 아래 정의에 따라 엄격하게 분류하십시오.\n\n"
        )

        category_rules = {
            'Investment': (
                "■ 신호(Signal) 정의:\n"
                "- 거시 경제 지표(GDP, CPI, 금리, 환율 등)의 구체적 수치 변화\n"
                "- 자산 가격(주가, 원자재, 채권 등)의 명확한 방향성과 변동폭\n"
                "- 기업 실적, 정책 결정 등 검증 가능한 팩트\n\n"
                "■ 소음(Noise) 정의:\n"
                "- '오를 수도 있고 내릴 수도 있다' 식의 무가치 전망 -> 라벨: tautology\n"
                "- '폭락', '대폭등', '공포' 등 자극적 수식어 -> 라벨: fear_greed\n"
                "- 근거 없는 목표가, 확증 편향적 낙관/비관 -> 라벨: ungrounded_prediction\n"
                "- 광고성 종목 추천, 리딩방 유도 -> 라벨: promotion"
            ),
            'Affairs': (
                "■ 신호(Signal) 정의:\n"
                "- 법안, 제도 변화의 구체적 내용과 시행 일정\n"
                "- 지정학적 분쟁, 외교 사건의 사실관계 (누가, 언제, 무엇을)\n"
                "- 공식 발표, 통계, 판결문 등 검증 가능한 1차 출처\n\n"
                "■ 소음(Noise) 정의:\n"
                "- 특정 정치 진영의 편향된 프레이밍 -> 라벨: political_bias\n"
                "- 사실 전달이 아닌 가치 판단, 도덕적 훈계 -> 라벨: value_judgment\n"
                "- 본질과 무관한 인신공격, 조롱, 비아냥 -> 라벨: ad_hominem\n"
                "- 감정적 호소, 분노 유발 수사법 -> 라벨: emotional_appeal"
            ),
            'Popular Science': (
                "■ 신호(Signal) 정의:\n"
                "- 기술, 현상의 핵심 작동 메커니즘에 대한 정확한 설명\n"
                "- 기존 한계 돌파 여부, 벤치마크 수치, 실험 결과\n"
                "- 실용적 적용 가능성과 구체적 타임라인\n\n"
                "■ 소음(Noise) 정의:\n"
                "- 실현 가능성이 입증되지 않은 과장된 기대감 -> 라벨: hype\n"
                "- 설명에 기여하지 않는 학술 용어 나열 -> 라벨: jargon_overload\n"
                "- '혁명적', '게임체인저' 등 내용 없는 수식어 -> 라벨: empty_modifier\n"
                "- SF적 상상을 사실처럼 서술 -> 라벨: speculation"
            )
        }

        return base + category_rules.get(category, category_rules['Affairs'])

    def _get_analysis_schema(self):
        return {
            "type": "OBJECT",
            "properties": {
                "core_fact": {
                    "type": "ARRAY",
                    "description": "구체적 수치와 명확한 방향성을 지닌 객관적 사실.",
                    "items": {"type": "STRING"}
                },
                "actionable_insight": {
                    "type": "ARRAY",
                    "description": "core_fact에 기반한 논리적 추론 및 시사점.",
                    "items": {"type": "STRING"}
                },
                "noise_analysis": {
                    "type": "ARRAY",
                    "description": "정보가 없는 발언의 추출과 라벨링.",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "quote": {"type": "STRING", "description": "원문에서 추출한 소음 발언 (직접 인용)"},
                            "label": {"type": "STRING", "description": "소음 유형 라벨"}
                        },
                        "required": ["quote", "label"]
                    }
                },
                "information_value": {
                    "type": "OBJECT",
                    "description": "전체 텍스트의 신호 대 소음 비율 평가.",
                    "properties": {
                        "score": {"type": "INTEGER", "description": "정보 가치 점수 (0-100)"},
                        "grade": {"type": "STRING", "description": "등급 (A, B, C, D, F)"},
                        "signal_ratio": {"type": "STRING", "description": "신호 비율 (예: '72%')"},
                        "reasoning": {"type": "STRING", "description": "평가 근거 1줄 요약"}
                    },
                    "required": ["score", "grade", "signal_ratio", "reasoning"]
                }
            },
            "required": ["core_fact", "actionable_insight", "noise_analysis", "information_value"]
        }

    def _get_briefing_schema(self):
        return {
            "type": "OBJECT",
            "properties": {
                "investment": {"type": "STRING", "description": "투자 카테고리 핵심 요약"},
                "affairs": {"type": "STRING", "description": "시사 카테고리 핵심 요약"},
                "science": {"type": "STRING", "description": "과학 카테고리 핵심 요약"},
                "insight": {"type": "STRING", "description": "오늘의 주요 시사점"},
                "htmlBody": {"type": "STRING", "description": "Blogger 게시용 HTML 본문"}
            },
            "required": ["investment", "affairs", "science", "insight", "htmlBody"]
        }

    def analyze_video(self, video_data, model_name):
        schema = self._get_analysis_schema()
        system_instruction = self._get_system_instruction(video_data['category'])
        
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction
        )
        
        prompt = f"아래 영상 텍스트에서 신호와 소음을 분리 분석하십시오.\n\n제목: {video_data['title']}\n채널: {video_data['channel']}\n"
        
        if video_data.get('transcript'):
            prompt += f"\n[전체 자막 스크립트]\n{video_data['transcript'][:30000]}"
        else:
            prompt += f"\n[영상 설명]\n{video_data['description']}"

        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=schema
                )
            )
            
            result = json.loads(response.text)
            return result
        except Exception as e:
            print(f"  [분석 실패] {video_data['title']}: {str(e)}")
            return None

    def generate_briefing(self, summaries, model_name):
        schema = self._get_briefing_schema()
        model = genai.GenerativeModel(model_name=model_name)
        
        prompt = (
            "아래 영상 요약을 바탕으로 '오늘의 브리핑'을 작성해줘.\n"
            "카테고리별 핵심 3줄 + 주요 시사점 1줄 + Blogger HTML 본문.\n\n"
            f"{json.dumps(summaries, ensure_ascii=False)}"
        )

        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=schema
                )
            )
            
            result = json.loads(response.text)
            return result
        except Exception as e:
            print(f"  [브리핑 생성 실패] {str(e)}")
            return None