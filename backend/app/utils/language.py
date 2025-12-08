"""
NyayamGPT - Language Utilities
==============================
Multilingual support and translation utilities.
"""

from typing import Optional

from app.core.logging import logger


# Supported languages
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "or": "Odia",
}


# Common legal term translations (English to Hindi)
LEGAL_TERMS_HINDI = {
    "section": "धारा",
    "punishment": "सजा",
    "imprisonment": "कारावास",
    "fine": "जुर्माना",
    "offense": "अपराध",
    "accused": "आरोपी",
    "victim": "पीड़ित",
    "court": "न्यायालय",
    "judge": "न्यायाधीश",
    "lawyer": "वकील",
    "bail": "जमानत",
    "warrant": "वारंट",
    "FIR": "प्रथम सूचना रिपोर्ट",
    "complaint": "शिकायत",
    "evidence": "साक्ष्य",
    "witness": "गवाह",
    "trial": "मुकदमा",
    "verdict": "फैसला",
    "appeal": "अपील",
    "conviction": "दोषसिद्धि",
    "acquittal": "बरी",
    "death penalty": "मृत्युदंड",
    "life imprisonment": "आजीवन कारावास",
    "cognizable": "संज्ञेय",
    "non-cognizable": "असंज्ञेय",
    "bailable": "जमानती",
    "non-bailable": "गैर-जमानती",
    "murder": "हत्या",
    "theft": "चोरी",
    "fraud": "धोखाधड़ी",
    "cheating": "छल",
    "rape": "बलात्कार",
    "assault": "हमला",
    "robbery": "डकैती",
    "kidnapping": "अपहरण",
}


def is_language_supported(language_code: str) -> bool:
    """
    Check if a language is supported.
    
    Args:
        language_code: ISO language code
        
    Returns:
        bool: Whether language is supported
    """
    return language_code.lower() in SUPPORTED_LANGUAGES


def get_language_name(language_code: str) -> str:
    """
    Get language name from code.
    
    Args:
        language_code: ISO language code
        
    Returns:
        str: Language name or code if not found
    """
    return SUPPORTED_LANGUAGES.get(language_code.lower(), language_code)


def detect_language(text: str) -> str:
    """
    Detect the language of input text.
    
    Simple detection based on character sets.
    
    Args:
        text: Input text
        
    Returns:
        str: Detected language code
    """
    # Count character types
    devanagari = sum(1 for c in text if '\u0900' <= c <= '\u097F')  # Hindi, Marathi
    bengali = sum(1 for c in text if '\u0980' <= c <= '\u09FF')
    gurmukhi = sum(1 for c in text if '\u0A00' <= c <= '\u0A7F')   # Punjabi
    gujarati = sum(1 for c in text if '\u0A80' <= c <= '\u0AFF')
    odia = sum(1 for c in text if '\u0B00' <= c <= '\u0B7F')
    tamil = sum(1 for c in text if '\u0B80' <= c <= '\u0BFF')
    telugu = sum(1 for c in text if '\u0C00' <= c <= '\u0C7F')
    kannada = sum(1 for c in text if '\u0C80' <= c <= '\u0CFF')
    malayalam = sum(1 for c in text if '\u0D00' <= c <= '\u0D7F')
    
    total = len(text.replace(" ", ""))
    if total == 0:
        return "en"
    
    # Determine dominant script
    if devanagari / total > 0.3:
        return "hi"
    elif bengali / total > 0.3:
        return "bn"
    elif gurmukhi / total > 0.3:
        return "pa"
    elif gujarati / total > 0.3:
        return "gu"
    elif odia / total > 0.3:
        return "or"
    elif tamil / total > 0.3:
        return "ta"
    elif telugu / total > 0.3:
        return "te"
    elif kannada / total > 0.3:
        return "kn"
    elif malayalam / total > 0.3:
        return "ml"
    else:
        return "en"


def translate_legal_terms(text: str, target_language: str) -> str:
    """
    Translate common legal terms in text.
    
    Note: This is a simple word replacement. For full translation,
    use a proper translation API.
    
    Args:
        text: Text to translate
        target_language: Target language code
        
    Returns:
        str: Text with translated terms
    """
    if target_language != "hi":
        logger.debug(f"Translation to {target_language} not supported yet")
        return text
    
    result = text
    for english, hindi in LEGAL_TERMS_HINDI.items():
        # Case-insensitive replacement
        import re
        pattern = rf"\b{re.escape(english)}\b"
        result = re.sub(
            pattern,
            f"{english} ({hindi})",
            result,
            flags=re.IGNORECASE,
            count=1  # Only first occurrence
        )
    
    return result


def format_response_language_hint(language: str) -> str:
    """
    Get a prompt hint for response language.
    
    Args:
        language: Target language code
        
    Returns:
        str: Prompt instruction for language
    """
    language_name = get_language_name(language)
    
    if language == "en":
        return "Respond in clear, simple English."
    elif language == "hi":
        return "Respond in Hindi (हिंदी), using Devanagari script. Include English legal terms with Hindi explanations."
    else:
        return f"Respond in {language_name}. Include English legal terms where appropriate."


# Greeting templates for different languages
GREETINGS = {
    "en": "Hello! I'm NyayamGPT, your Indian legal assistant. How can I help you today?",
    "hi": "नमस्ते! मैं न्यायमGPT हूं, आपका भारतीय कानूनी सहायक। आज मैं आपकी कैसे मदद कर सकता हूं?",
    "bn": "নমস্কার! আমি NyayamGPT, আপনার ভারতীয় আইনি সহকারী। আজ আমি আপনাকে কিভাবে সাহায্য করতে পারি?",
    "ta": "வணக்கம்! நான் NyayamGPT, உங்கள் இந்திய சட்ட உதவியாளர். இன்று நான் உங்களுக்கு எவ்வாறு உதவ முடியும்?",
}


def get_greeting(language: str) -> str:
    """
    Get greeting in specified language.
    
    Args:
        language: Language code
        
    Returns:
        str: Greeting message
    """
    return GREETINGS.get(language, GREETINGS["en"])


# Disclaimer in different languages
DISCLAIMERS = {
    "en": "⚠️ Disclaimer: This information is for educational purposes only and should not be considered legal advice. For specific legal matters, please consult a qualified lawyer.",
    "hi": "⚠️ अस्वीकरण: यह जानकारी केवल शैक्षिक उद्देश्यों के लिए है और इसे कानूनी सलाह नहीं माना जाना चाहिए। विशिष्ट कानूनी मामलों के लिए, कृपया किसी योग्य वकील से परामर्श करें।",
}


def get_disclaimer(language: str) -> str:
    """
    Get disclaimer in specified language.
    
    Args:
        language: Language code
        
    Returns:
        str: Disclaimer message
    """
    return DISCLAIMERS.get(language, DISCLAIMERS["en"])
