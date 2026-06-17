import re
from typing import Dict, List, Any


class SpamAnalyzer:
    def __init__(self) -> None:
        # Standard spam trigger words/phrases
        self.spam_words = [
            "completely free", "100% free", "act now", "apply online", "buy now", 
            "click here", "double your", "earn money", "eliminate debt", "get paid", 
            "make money", "million dollars", "no catch", "no cost", "no fees", 
            "no interest", "no investment", "pure profit", "save money", "special promotion", 
            "this is not spam", "urgently", "winner", "you are a winner", "extra cash",
            "risk free", "limited time", "special offer", "guaranteed", "lowest price",
            "opportunity", "easy money", "free access", "hidden charges", "cancel at any time",
            "be your own boss", "get rich", "fast cash", "multi-level marketing"
        ]

    def _count_syllables_english(self, word: str) -> int:
        word = word.lower()
        if len(word) <= 3:
            return 1
        
        # Simple vowel counting
        vowels = "aeiouy"
        count = 0
        prev_is_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_is_vowel:
                count += 1
            prev_is_vowel = is_vowel
            
        # Silent 'e' adjustments
        if word.endswith("e"):
            count -= 1
        if word.endswith("le") and len(word) > 2 and word[-3] not in vowels:
            count += 1
            
        return max(1, count)

    def _count_syllables_turkish(self, word: str) -> int:
        # Turkish syllables are exactly equal to the number of vowels
        turkish_vowels = "aeıioöuü"
        count = sum(1 for char in word.lower() if char in turkish_vowels)
        return max(1, count)

    def analyze(self, subject: str, body: str, language: str = "English") -> Dict[str, Any]:
        full_text = f"{subject} {body}".lower()
        
        # 1. Spam analysis
        matches = []
        for word in self.spam_words:
            # Use regex to match whole phrase/word
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, full_text):
                matches.append(word)
                
        # Calculate spam density/risk
        match_count = len(matches)
        if match_count == 0:
            risk = "Low"
            score = 0
        elif match_count <= 2:
            risk = "Medium"
            score = 30 + (match_count * 10)
        else:
            risk = "High"
            score = min(100, 60 + (match_count * 8))
            
        # 2. Readability analysis
        # Clean text for counting
        cleaned_body = re.sub(r'[^\w\s\.\!\?]', '', body)
        
        # Count sentences
        sentences = [s.strip() for s in re.split(r'[\.\!\?]+', cleaned_body) if s.strip()]
        sentence_count = len(sentences)
        
        # Count words
        words = [w.strip() for w in cleaned_body.split() if w.strip()]
        word_count = len(words)
        
        if word_count == 0 or sentence_count == 0:
            return {
                "spam_risk": risk,
                "spam_score": score,
                "spam_matches": matches,
                "readability_score": 100,
                "readability_level": "Easy",
                "word_count": 0,
                "sentence_count": 0
            }
            
        # Syllables count
        is_turkish = language.lower() in ["turkish", "türkçe", "tr"]
        if is_turkish:
            total_syllables = sum(self._count_syllables_turkish(w) for w in words)
        else:
            total_syllables = sum(self._count_syllables_english(w) for w in words)
            
        # Flesch Reading Ease score calculation
        # FRE = 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
        asl = word_count / sentence_count  # Average Sentence Length
        asw = total_syllables / word_count # Average Syllables per Word
        
        fre = 206.835 - (1.015 * asl) - (84.6 * asw)
        fre = max(0.0, min(100.0, fre))
        
        # Map score to level
        if fre >= 70:
            level = "Easy"
        elif fre >= 50:
            level = "Medium"
        else:
            level = "Hard"
            
        return {
            "spam_risk": risk,
            "spam_score": score,
            "spam_matches": matches,
            "readability_score": round(fre, 1),
            "readability_level": level,
            "word_count": word_count,
            "sentence_count": sentence_count
        }
