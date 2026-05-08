"""
JYOTISH ENGINE - AI INTENT CLASSIFIER
Understands any language, spelling mistakes, 290+ life categories
"""

import httpx
from typing import Dict, List, Optional
from datetime import datetime


class IntentClassifier:
    """
    AI-powered intent classification for astrology queries
    
    Features:
    - Multi-language support (Hindi, Hinglish, English, etc.)
    - Spelling mistake tolerance
    - 290+ life category classification
    - House mapping for astrological analysis
    - Time period extraction
    """
    
    # Category to House mapping
    CATEGORY_HOUSES = {
        # RELATIONSHIPS (House 7)
        'MARRIAGE': 7, 'LOVE': 5, 'DIVORCE': 7, 'BOYFRIEND': 5, 'GIRLFRIEND': 5,
        'EX': 7, 'AFFAIR': 5, 'COMPATIBILITY': 7, 'SOULMATE': 7, 'DATING': 5,
        'COMMITMENT': 7, 'TRUST': 7, 'CHEATING': 7, 'LONG_DISTANCE': 7,
        'ARRANGED_MARRIAGE': 7, 'LOVE_MARRIAGE': 7, 'SPOUSE': 7, 'PARTNER': 7,
        
        # FAMILY (House 4)
        'MOTHER': 4, 'FATHER': 9, 'PARENTS': 4, 'SIBLINGS': 3, 'BROTHER': 3,
        'SISTER': 3, 'CHILDREN': 5, 'SON': 5, 'DAUGHTER': 5, 'BABY': 5,
        'PREGNANCY': 5, 'FERTILITY': 5, 'ADOPTION': 5, 'GRANDPARENTS': 9,
        'IN_LAWS': 7, 'JOINT_FAMILY': 4, 'FAMILY_CONFLICT': 4, 'INHERITANCE': 8,
        
        # CAREER (House 10)
        'JOB': 10, 'CAREER': 10, 'PROMOTION': 10, 'SALARY': 2, 'BOSS': 10,
        'COLLEAGUES': 6, 'OFFICE': 10, 'WORK_LIFE_BALANCE': 10, 'INTERVIEW': 10,
        'RESUME': 10, 'FIRED': 10, 'RESIGN': 10, 'CAREER_CHANGE': 10,
        'BUSINESS': 7, 'STARTUP': 10, 'ENTREPRENEURSHIP': 10, 'PARTNERSHIP_BIZ': 7,
        'CLIENTS': 7, 'FREELANCE': 10, 'REMOTE_WORK': 10, 'INTERNSHIP': 10,
        'FIRST_JOB': 10, 'RETIREMENT': 10, 'GOVERNMENT_JOB': 10, 'PRIVATE_JOB': 10,
        
        # MONEY (House 2, 11)
        'MONEY': 2, 'WEALTH': 2, 'SAVINGS': 2, 'INVESTMENT': 5, 'STOCKS': 5,
        'MUTUAL_FUNDS': 5, 'CRYPTO': 8, 'GOLD': 2, 'PROPERTY': 4, 'HOUSE': 4,
        'LAND': 4, 'RENT': 4, 'DEBT': 6, 'LOAN': 6, 'EMI': 6, 'CREDIT_CARD': 6,
        'BANKRUPTCY': 8, 'LOTTERY': 5, 'INHERITANCE_MONEY': 8, 'TAX': 8,
        'INSURANCE': 8, 'FINANCIAL_FREEDOM': 11, 'INCOME': 11, 'GAINS': 11,
        
        # EDUCATION (House 4, 5, 9)
        'EDUCATION': 4, 'SCHOOL': 4, 'COLLEGE': 9, 'UNIVERSITY': 9, 'EXAMS': 5,
        'BOARDS': 4, 'ENTRANCE': 5, 'JEE': 5, 'NEET': 5, 'UPSC': 10, 'CAT': 5,
        'GATE': 5, 'IELTS': 9, 'TOEFL': 9, 'GRE': 9, 'RESULTS': 5, 'MARKS': 5,
        'FAIL': 5, 'TOPPER': 5, 'MASTERS': 9, 'PHD': 9, 'RESEARCH': 9,
        'SCHOLARSHIP': 9, 'SKILLS': 3, 'CERTIFICATION': 5, 'COACHING': 4,
        
        # TRAVEL (House 9, 12)
        'TRAVEL': 9, 'VACATION': 9, 'TRIP': 3, 'ABROAD': 12, 'FOREIGN': 12,
        'USA': 12, 'UK': 12, 'CANADA': 12, 'AUSTRALIA': 12, 'EUROPE': 12,
        'DUBAI': 12, 'VISA': 12, 'IMMIGRATION': 12, 'GREEN_CARD': 12, 'PR': 12,
        'H1B': 12, 'STUDENT_VISA': 12, 'PASSPORT': 12, 'RELOCATION': 4,
        'SHIFTING': 4, 'PILGRIMAGE': 9, 'FLIGHT': 3,
        
        # HEALTH (House 6, 8)
        'HEALTH': 6, 'FITNESS': 6, 'WEIGHT': 6, 'DIET': 6, 'ILLNESS': 6,
        'DISEASE': 6, 'HOSPITAL': 8, 'DOCTOR': 6, 'SURGERY': 8, 'ACCIDENT': 8,
        'RECOVERY': 6, 'CANCER': 8, 'HEART': 6, 'DIABETES': 6, 'BP': 6,
        'THYROID': 6, 'MENTAL_HEALTH': 6, 'ANXIETY': 6, 'DEPRESSION': 6,
        'STRESS': 6, 'SLEEP': 12, 'ADDICTION': 12, 'ALCOHOL': 12, 'SMOKING': 6,
        'THERAPY': 12, 'MEDITATION': 12, 'YOGA': 12, 'AYURVEDA': 6,
        
        # LEGAL (House 6, 7)
        'LEGAL': 7, 'COURT': 6, 'LAWYER': 7, 'LAWSUIT': 6, 'POLICE': 6,
        'CRIME': 8, 'JAIL': 12, 'BAIL': 12, 'PROPERTY_DISPUTE': 4, 'DIVORCE_CASE': 7,
        'CUSTODY': 5, 'CONTRACTS': 7, 'DOCUMENTS': 3, 'SETTLEMENT': 7,
        
        # SPIRITUAL (House 9, 12)
        'SPIRITUAL': 9, 'RELIGION': 9, 'GOD': 9, 'TEMPLE': 9, 'PRAYER': 9,
        'KARMA': 8, 'PAST_LIFE': 12, 'MOKSHA': 12, 'ASTROLOGY': 8, 'KUNDLI': 8,
        'DASHA': 8, 'REMEDY': 6, 'MANTRA': 9, 'GEMSTONE': 1, 'PUJA': 9,
        'GURU': 9, 'OCCULT': 8, 'DREAMS': 12, 'INTUITION': 12, 'PSYCHIC': 8,
        
        # EMOTIONS (House 1, 4)
        'HAPPY': 1, 'SAD': 4, 'ANGRY': 1, 'SCARED': 8, 'CONFUSED': 12,
        'STUCK': 12, 'LONELY': 12, 'HOPELESS': 12, 'ANXIOUS': 6, 'JEALOUS': 6,
        'GUILTY': 8, 'SHAME': 12, 'CONFIDENT': 1, 'MOTIVATED': 1, 'LAZY': 6,
        'BORED': 3, 'EXCITED': 5, 'PEACEFUL': 12, 'RESTLESS': 3,
        
        # LIFE PURPOSE (House 1, 9, 10)
        'LIFE_PURPOSE': 9, 'DESTINY': 9, 'LUCK': 9, 'SUCCESS': 10, 'FAILURE': 6,
        'OBSTACLES': 6, 'ENEMIES': 6, 'COMPETITION': 6, 'REPUTATION': 10,
        'FAME': 10, 'SECRETS': 8, 'LIES': 8, 'BETRAYAL': 8, 'REVENGE': 8,
        'FORGIVENESS': 12, 'REGRET': 12, 'CHANGE': 8, 'NEW_BEGINNING': 1,
        'ENDING': 12, 'WAITING': 12, 'TIMING': 8, 'DECISION': 3, 'RISK': 5,
        'SAFETY': 4, 'FREEDOM': 11,
        
        # DEFAULT
        'GENERAL': 1, 'UNKNOWN': 1,
    }
    
    # Search duration by category (months)
    CATEGORY_SEARCH_MONTHS = {
        'MARRIAGE': 60, 'LOVE': 24, 'CHILDREN': 48, 'PREGNANCY': 24,
        'JOB': 12, 'CAREER': 24, 'PROMOTION': 12, 'BUSINESS': 36,
        'ABROAD': 36, 'VISA': 18, 'IMMIGRATION': 48,
        'PROPERTY': 36, 'HOUSE': 36, 'WEALTH': 60,
        'HEALTH': 12, 'SURGERY': 12, 'RECOVERY': 6,
        'EDUCATION': 24, 'EXAMS': 6, 'RESULTS': 3,
        'GENERAL': 12,
    }
    
    # Favorable planets by category
    CATEGORY_PLANETS = {
        'MARRIAGE': ['Venus', 'Jupiter', 'Moon'],
        'LOVE': ['Venus', 'Moon', 'Mars'],
        'CHILDREN': ['Jupiter', 'Moon', 'Venus'],
        'CAREER': ['Sun', 'Saturn', 'Jupiter'],
        'JOB': ['Saturn', 'Jupiter', 'Mercury'],
        'BUSINESS': ['Mercury', 'Jupiter', 'Sun'],
        'MONEY': ['Jupiter', 'Venus', 'Moon'],
        'WEALTH': ['Jupiter', 'Venus', 'Mercury'],
        'PROPERTY': ['Mars', 'Saturn', 'Moon'],
        'ABROAD': ['Rahu', 'Moon', 'Jupiter'],
        'HEALTH': ['Sun', 'Moon', 'Jupiter'],
        'EDUCATION': ['Jupiter', 'Mercury', 'Moon'],
        'SPIRITUAL': ['Jupiter', 'Ketu', 'Moon'],
    }
    
    def __init__(self, api_key: str, model: str = "openai/gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
    
    async def classify(self, message: str, user_context: dict = None) -> Dict:
        """Classify user message into astrological intent"""
        
        classification_prompt = f"""You are an intent classifier for a Vedic astrology app.

USER MESSAGE: "{message}"

Analyze this message in ANY language (Hindi, Hinglish, English, Tamil, etc.) and extract:

1. CATEGORY: The main life topic. Pick ONE from:
   MARRIAGE, LOVE, DIVORCE, BOYFRIEND, GIRLFRIEND, SOULMATE, DATING, SPOUSE, PARTNER,
   MOTHER, FATHER, CHILDREN, PREGNANCY, FAMILY, SIBLINGS,
   JOB, CAREER, PROMOTION, BUSINESS, INTERVIEW, FIRED, RESIGN,
   MONEY, WEALTH, SALARY, INVESTMENT, PROPERTY, DEBT, LOAN,
   EDUCATION, EXAMS, COLLEGE, RESULTS, SCHOLARSHIP,
   TRAVEL, ABROAD, VISA, IMMIGRATION, RELOCATION,
   HEALTH, ILLNESS, SURGERY, MENTAL_HEALTH, ANXIETY, DEPRESSION,
   SPIRITUAL, KARMA, DESTINY, LIFE_PURPOSE,
   LEGAL, COURT, LAWSUIT,
   GENERAL

2. QUESTION_TYPE: What are they asking?
   - TIMING (when will something happen)
   - PREDICTION (will something happen)
   - GUIDANCE (what should I do)
   - ANALYSIS (why is this happening)
   - CONFIRMATION (is this right)
   - EMOTIONAL (feeling/venting)

3. TIME_REFERENCE: Any time mentioned
   - PAST, PRESENT, NEAR_FUTURE, FAR_FUTURE, SPECIFIC, NONE

4. EMOTION: User's emotional state
   - ANXIOUS, HOPEFUL, SAD, CONFUSED, EXCITED, NEUTRAL, DESPERATE, ANGRY, PEACEFUL

5. URGENCY: HIGH, MEDIUM, LOW

Respond in this EXACT JSON format only:
{{"category": "CATEGORY", "question_type": "TYPE", "time_reference": "TIME", "emotion": "EMOTION", "urgency": "URGENCY", "extracted_topic": "brief topic"}}"""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "Respond ONLY with valid JSON."},
                            {"role": "user", "content": classification_prompt}
                        ],
                        "max_tokens": 150,
                        "temperature": 0.1
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    return self._fallback_classification(message)
                
                data = response.json()
                result_text = data["choices"][0]["message"]["content"].strip()
                
                import json
                result_text = result_text.replace("```json", "").replace("```", "").strip()
                result = json.loads(result_text)
                
                category = result.get('category', 'GENERAL').upper()
                house = self.CATEGORY_HOUSES.get(category, 1)
                search_months = self.CATEGORY_SEARCH_MONTHS.get(category, 12)
                favorable_planets = self.CATEGORY_PLANETS.get(category, ['Jupiter'])
                
                return {
                    'success': True,
                    'category': category,
                    'house': house,
                    'question_type': result.get('question_type', 'GUIDANCE'),
                    'time_reference': result.get('time_reference', 'NONE'),
                    'emotion': result.get('emotion', 'NEUTRAL'),
                    'urgency': result.get('urgency', 'MEDIUM'),
                    'extracted_topic': result.get('extracted_topic', message[:50]),
                    'search_months': search_months,
                    'favorable_planets': favorable_planets,
                    'original_message': message,
                }
        
        except Exception as e:
            print(f"Classification error: {e}")
            return self._fallback_classification(message)
    
    def _fallback_classification(self, message: str) -> Dict:
        """Fallback classification using keyword matching"""
        message_lower = message.lower()
        
        keywords = {
            'MARRIAGE': ['marriage', 'shaadi', 'shadi', 'wedding', 'marry', 'vivah', 'wife', 'husband'],
            'LOVE': ['love', 'pyar', 'mohabbat', 'relationship', 'boyfriend', 'girlfriend', 'crush', 'bf', 'gf'],
            'JOB': ['job', 'naukri', 'kaam', 'work', 'employment', 'hire', 'interview'],
            'CAREER': ['career', 'promotion', 'success', 'professional', 'growth'],
            'MONEY': ['money', 'paisa', 'wealth', 'rich', 'income', 'salary', 'financial'],
            'HEALTH': ['health', 'sehat', 'illness', 'doctor', 'hospital', 'disease', 'sick'],
            'EDUCATION': ['study', 'padhai', 'exam', 'college', 'school', 'university', 'degree'],
            'CHILDREN': ['child', 'baby', 'baccha', 'pregnancy', 'pregnant', 'son', 'daughter'],
            'ABROAD': ['abroad', 'foreign', 'videsh', 'usa', 'canada', 'uk', 'visa', 'immigration'],
            'PROPERTY': ['property', 'house', 'ghar', 'land', 'zameen', 'flat', 'apartment'],
        }
        
        for category, words in keywords.items():
            if any(word in message_lower for word in words):
                return {
                    'success': True,
                    'category': category,
                    'house': self.CATEGORY_HOUSES.get(category, 1),
                    'question_type': 'GUIDANCE',
                    'time_reference': 'NONE',
                    'emotion': 'NEUTRAL',
                    'urgency': 'MEDIUM',
                    'extracted_topic': category.lower(),
                    'search_months': self.CATEGORY_SEARCH_MONTHS.get(category, 12),
                    'favorable_planets': self.CATEGORY_PLANETS.get(category, ['Jupiter']),
                    'original_message': message,
                }
        
        return {
            'success': True,
            'category': 'GENERAL',
            'house': 1,
            'question_type': 'GUIDANCE',
            'time_reference': 'NONE',
            'emotion': 'NEUTRAL',
            'urgency': 'MEDIUM',
            'extracted_topic': 'general inquiry',
            'search_months': 12,
            'favorable_planets': ['Jupiter'],
            'original_message': message,
        }
    
    def get_house_significations(self, house: int) -> Dict:
        """Get significations of a house"""
        significations = {
            1: {'name': 'Self', 'rules': 'Body, personality, health, new beginnings'},
            2: {'name': 'Wealth', 'rules': 'Money, family, speech, possessions'},
            3: {'name': 'Siblings', 'rules': 'Brothers, sisters, courage, communication'},
            4: {'name': 'Home', 'rules': 'Mother, home, property, vehicles, peace'},
            5: {'name': 'Children', 'rules': 'Children, creativity, romance, education'},
            6: {'name': 'Enemies', 'rules': 'Enemies, debts, disease, service'},
            7: {'name': 'Marriage', 'rules': 'Spouse, partner, marriage, business'},
            8: {'name': 'Transformation', 'rules': 'Death, inheritance, secrets, occult'},
            9: {'name': 'Fortune', 'rules': 'Luck, father, guru, religion, travel'},
            10: {'name': 'Career', 'rules': 'Career, profession, status, authority'},
            11: {'name': 'Gains', 'rules': 'Income, gains, friends, wishes'},
            12: {'name': 'Loss', 'rules': 'Losses, foreign lands, spirituality, moksha'},
        }
        return significations.get(house, significations[1])


_classifier = None

def get_classifier(api_key: str) -> IntentClassifier:
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier(api_key)
    return _classifier


async def classify_intent(message: str, api_key: str) -> Dict:
    classifier = get_classifier(api_key)
    return await classifier.classify(message)
