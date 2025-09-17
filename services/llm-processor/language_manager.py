#!/usr/bin/env python3
"""
Language Manager for Hey Raven
Handles multi-language support for wake word detection, LLM responses, and TTS.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)

@dataclass
class LanguageConfig:
    """Language configuration for Hey Raven."""
    code: str  # ISO 639-1 code (e.g., 'en', 'es', 'fr')
    name: str  # Full language name
    wake_words: List[str]  # Wake word patterns for this language
    tts_voice: str  # TTS voice identifier
    llm_prompt_template: str  # Language-specific prompt template

class LanguageManager:
    """Manages multi-language support for Hey Raven."""
    
    def __init__(self):
        self.supported_languages = self._initialize_languages()
        self.default_language = 'en'
        
    def _initialize_languages(self) -> Dict[str, LanguageConfig]:
        """Initialize supported languages configuration."""
        return {
            'en': LanguageConfig(
                code='en',
                name='English',
                wake_words=[
                    'hey raven', 'hello raven', 'hi raven', 'okay raven',
                    'raven can you', 'raven could you', 'raven will you',
                    'raven what', 'raven where', 'raven when', 'raven who',
                    'raven why', 'raven how', 'raven,', 'raven?'
                ],
                tts_voice='en',
                llm_prompt_template=(
                    "You are Raven, a helpful AI assistant integrated into a meeting system. "
                    "Provide concise, helpful responses to questions during meetings. "
                    "Keep responses brief and relevant to the meeting context. "
                    "Respond in English."
                )
            ),
            'es': LanguageConfig(
                code='es',
                name='Spanish',
                wake_words=[
                    'hey raven', 'hola raven', 'oye raven', 'escucha raven',
                    'raven puedes', 'raven podrías', 'raven qué', 'raven dónde',
                    'raven cuándo', 'raven quién', 'raven por qué', 'raven cómo',
                    'raven,', 'raven?'
                ],
                tts_voice='es',
                llm_prompt_template=(
                    "Eres Raven, un asistente de IA útil integrado en un sistema de reuniones. "
                    "Proporciona respuestas concisas y útiles a las preguntas durante las reuniones. "
                    "Mantén las respuestas breves y relevantes al contexto de la reunión. "
                    "Responde en español."
                )
            ),
            'fr': LanguageConfig(
                code='fr',
                name='French',
                wake_words=[
                    'hey raven', 'salut raven', 'bonjour raven', 'écoute raven',
                    'raven peux-tu', 'raven pourrais-tu', 'raven qu\'est-ce que',
                    'raven où', 'raven quand', 'raven qui', 'raven pourquoi',
                    'raven comment', 'raven,', 'raven?'
                ],
                tts_voice='fr',
                llm_prompt_template=(
                    "Tu es Raven, un assistant IA utile intégré dans un système de réunion. "
                    "Fournis des réponses concises et utiles aux questions pendant les réunions. "
                    "Garde les réponses brèves et pertinentes au contexte de la réunion. "
                    "Réponds en français."
                )
            ),
            'de': LanguageConfig(
                code='de',
                name='German',
                wake_words=[
                    'hey raven', 'hallo raven', 'hör zu raven', 'okay raven',
                    'raven kannst du', 'raven könntest du', 'raven was',
                    'raven wo', 'raven wann', 'raven wer', 'raven warum',
                    'raven wie', 'raven,', 'raven?'
                ],
                tts_voice='de',
                llm_prompt_template=(
                    "Du bist Raven, ein hilfreicher KI-Assistent, der in ein Meeting-System integriert ist. "
                    "Gib prägnante, hilfreiche Antworten auf Fragen während Meetings. "
                    "Halte Antworten kurz und relevant zum Meeting-Kontext. "
                    "Antworte auf Deutsch."
                )
            ),
            'it': LanguageConfig(
                code='it',
                name='Italian',
                wake_words=[
                    'hey raven', 'ciao raven', 'ascolta raven', 'okay raven',
                    'raven puoi', 'raven potresti', 'raven cosa', 'raven dove',
                    'raven quando', 'raven chi', 'raven perché', 'raven come',
                    'raven,', 'raven?'
                ],
                tts_voice='it',
                llm_prompt_template=(
                    "Sei Raven, un assistente IA utile integrato in un sistema di riunioni. "
                    "Fornisci risposte concise e utili alle domande durante le riunioni. "
                    "Mantieni le risposte brevi e rilevanti al contesto della riunione. "
                    "Rispondi in italiano."
                )
            ),
            'pt': LanguageConfig(
                code='pt',
                name='Portuguese',
                wake_words=[
                    'hey raven', 'oi raven', 'olá raven', 'escuta raven',
                    'raven você pode', 'raven poderia', 'raven o que',
                    'raven onde', 'raven quando', 'raven quem', 'raven por que',
                    'raven como', 'raven,', 'raven?'
                ],
                tts_voice='pt',
                llm_prompt_template=(
                    "Você é Raven, um assistente de IA útil integrado em um sistema de reuniões. "
                    "Forneça respostas concisas e úteis para perguntas durante reuniões. "
                    "Mantenha as respostas breves e relevantes ao contexto da reunião. "
                    "Responda em português."
                )
            ),
            'ja': LanguageConfig(
                code='ja',
                name='Japanese',
                wake_words=[
                    'hey raven', 'こんにちは raven', 'レイブン', 'raven さん',
                    'raven は', 'raven を', 'raven が', 'raven の',
                    'raven に', 'raven で', 'raven,', 'raven?'
                ],
                tts_voice='ja',
                llm_prompt_template=(
                    "あなたはRavenです。会議システムに統合された有用なAIアシスタントです。"
                    "会議中の質問に対して簡潔で有用な回答を提供してください。"
                    "回答は短く、会議の文脈に関連性を保ってください。"
                    "日本語で回答してください。"
                )
            ),
            'zh': LanguageConfig(
                code='zh',
                name='Chinese',
                wake_words=[
                    'hey raven', '你好 raven', '雷文', 'raven 你',
                    'raven 可以', 'raven 能', 'raven 什么', 'raven 哪里',
                    'raven 什么时候', 'raven 谁', 'raven 为什么', 'raven 怎么',
                    'raven,', 'raven?'
                ],
                tts_voice='zh',
                llm_prompt_template=(
                    "你是Raven，一个集成在会议系统中的有用AI助手。"
                    "在会议期间为问题提供简洁、有用的回答。"
                    "保持回答简短并与会议内容相关。"
                    "用中文回答。"
                )
            )
        }

    def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detect language from text.
        Returns (language_code, confidence_score).
        """
        text_lower = text.lower()
        
        # Simple pattern-based detection
        language_scores = {}
        
        for lang_code, config in self.supported_languages.items():
            score = 0.0
            
            # Check for wake word patterns
            for wake_word in config.wake_words:
                if wake_word in text_lower:
                    score += 1.0
                    
            # Language-specific character patterns
            if lang_code == 'ja':
                # Check for Japanese characters
                if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text):
                    score += 0.8
            elif lang_code == 'zh':
                # Check for Chinese characters
                if re.search(r'[\u4E00-\u9FFF]', text):
                    score += 0.8
            elif lang_code == 'es':
                # Check for Spanish-specific patterns
                spanish_patterns = ['ñ', 'ü', 'qué', 'dónde', 'cuándo', 'cómo', 'por qué']
                for pattern in spanish_patterns:
                    if pattern in text_lower:
                        score += 0.3
            elif lang_code == 'fr':
                # Check for French-specific patterns
                french_patterns = ['ç', 'é', 'è', 'ê', 'ë', 'à', 'où', 'qu\'']
                for pattern in french_patterns:
                    if pattern in text_lower:
                        score += 0.3
            elif lang_code == 'de':
                # Check for German-specific patterns
                german_patterns = ['ä', 'ö', 'ü', 'ß', 'kannst', 'könntest', 'warum']
                for pattern in german_patterns:
                    if pattern in text_lower:
                        score += 0.3
                        
            language_scores[lang_code] = score
            
        # Find best match
        if language_scores:
            best_lang = max(language_scores.items(), key=lambda x: x[1])
            if best_lang[1] > 0:
                return best_lang[0], min(best_lang[1], 1.0)
                
        # Default to English
        return self.default_language, 0.5

    def get_language_config(self, language_code: str) -> LanguageConfig:
        """Get language configuration."""
        return self.supported_languages.get(language_code, 
                                           self.supported_languages[self.default_language])

    def get_wake_words_for_language(self, language_code: str) -> List[str]:
        """Get wake words for a specific language."""
        config = self.get_language_config(language_code)
        return config.wake_words

    def get_all_wake_words(self) -> Dict[str, List[str]]:
        """Get all wake words for all languages."""
        return {lang: config.wake_words for lang, config in self.supported_languages.items()}

    def build_multilingual_prompt(self, question: str, context: str = "", 
                                detected_language: Optional[str] = None) -> str:
        """Build a language-appropriate prompt."""
        if detected_language is None:
            detected_language, _ = self.detect_language(question)
            
        config = self.get_language_config(detected_language)
        
        # Build prompt with language-specific template
        prompt_parts = [config.llm_prompt_template]
        
        if context:
            if detected_language == 'es':
                prompt_parts.append(f"\nContexto de la reunión: {context}")
            elif detected_language == 'fr':
                prompt_parts.append(f"\nContexte de la réunion: {context}")
            elif detected_language == 'de':
                prompt_parts.append(f"\nMeeting-Kontext: {context}")
            elif detected_language == 'it':
                prompt_parts.append(f"\nContesto della riunione: {context}")
            elif detected_language == 'pt':
                prompt_parts.append(f"\nContexto da reunião: {context}")
            elif detected_language == 'ja':
                prompt_parts.append(f"\n会議のコンテキスト: {context}")
            elif detected_language == 'zh':
                prompt_parts.append(f"\n会议背景: {context}")
            else:
                prompt_parts.append(f"\nMeeting context: {context}")
                
        # Add question
        if detected_language == 'es':
            prompt_parts.append(f"\nPregunta: {question}")
            prompt_parts.append("\nRespuesta:")
        elif detected_language == 'fr':
            prompt_parts.append(f"\nQuestion: {question}")
            prompt_parts.append("\nRéponse:")
        elif detected_language == 'de':
            prompt_parts.append(f"\nFrage: {question}")
            prompt_parts.append("\nAntwort:")
        elif detected_language == 'it':
            prompt_parts.append(f"\nDomanda: {question}")
            prompt_parts.append("\nRisposta:")
        elif detected_language == 'pt':
            prompt_parts.append(f"\nPergunta: {question}")
            prompt_parts.append("\nResposta:")
        elif detected_language == 'ja':
            prompt_parts.append(f"\n質問: {question}")
            prompt_parts.append("\n回答:")
        elif detected_language == 'zh':
            prompt_parts.append(f"\n问题: {question}")
            prompt_parts.append("\n回答:")
        else:
            prompt_parts.append(f"\nQuestion: {question}")
            prompt_parts.append("\nResponse:")
            
        return "\n".join(prompt_parts)

    def get_tts_language(self, detected_language: str) -> str:
        """Get TTS language code for detected language."""
        config = self.get_language_config(detected_language)
        return config.tts_voice

    def translate_system_messages(self, message: str, target_language: str) -> str:
        """Translate common system messages."""
        translations = {
            'en': {
                'error': 'I apologize, but I encountered an error processing your request.',
                'no_response': 'I\'m sorry, I don\'t have a response for that question.',
                'processing': 'I\'m processing your request, please wait a moment.',
                'hello': 'Hello! How can I help you today?'
            },
            'es': {
                'error': 'Me disculpo, pero encontré un error al procesar su solicitud.',
                'no_response': 'Lo siento, no tengo una respuesta para esa pregunta.',
                'processing': 'Estoy procesando su solicitud, por favor espere un momento.',
                'hello': '¡Hola! ¿Cómo puedo ayudarte hoy?'
            },
            'fr': {
                'error': 'Je m\'excuse, mais j\'ai rencontré une erreur en traitant votre demande.',
                'no_response': 'Je suis désolé, je n\'ai pas de réponse à cette question.',
                'processing': 'Je traite votre demande, veuillez patienter un moment.',
                'hello': 'Bonjour! Comment puis-je vous aider aujourd\'hui?'
            },
            'de': {
                'error': 'Entschuldigung, aber ich bin auf einen Fehler bei der Bearbeitung Ihrer Anfrage gestoßen.',
                'no_response': 'Es tut mir leid, ich habe keine Antwort auf diese Frage.',
                'processing': 'Ich bearbeite Ihre Anfrage, bitte warten Sie einen Moment.',
                'hello': 'Hallo! Wie kann ich Ihnen heute helfen?'
            },
            'it': {
                'error': 'Mi scuso, ma ho riscontrato un errore nel processare la sua richiesta.',
                'no_response': 'Mi dispiace, non ho una risposta per quella domanda.',
                'processing': 'Sto processando la sua richiesta, per favore aspetti un momento.',
                'hello': 'Ciao! Come posso aiutarti oggi?'
            },
            'pt': {
                'error': 'Peço desculpas, mas encontrei um erro ao processar sua solicitação.',
                'no_response': 'Sinto muito, não tenho uma resposta para essa pergunta.',
                'processing': 'Estou processando sua solicitação, por favor aguarde um momento.',
                'hello': 'Olá! Como posso ajudá-lo hoje?'
            },
            'ja': {
                'error': '申し訳ございませんが、リクエストの処理中にエラーが発生しました。',
                'no_response': '申し訳ございませんが、その質問に対する回答がありません。',
                'processing': 'リクエストを処理中です。少々お待ちください。',
                'hello': 'こんにちは！今日はどのようにお手伝いできますか？'
            },
            'zh': {
                'error': '抱歉，处理您的请求时遇到了错误。',
                'no_response': '抱歉，我没有针对那个问题的回答。',
                'processing': '正在处理您的请求，请稍等片刻。',
                'hello': '您好！今天我可以为您做些什么？'
            }
        }
        
        lang_translations = translations.get(target_language, translations['en'])
        return lang_translations.get(message, message)

    def is_language_supported(self, language_code: str) -> bool:
        """Check if a language is supported."""
        return language_code in self.supported_languages

    def get_supported_languages(self) -> List[Tuple[str, str]]:
        """Get list of supported languages as (code, name) tuples."""
        return [(config.code, config.name) for config in self.supported_languages.values()]

# Global language manager instance
language_manager = LanguageManager()


