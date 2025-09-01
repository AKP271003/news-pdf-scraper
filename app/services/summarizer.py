#!/usr/bin/env python3
from openai import OpenAI
import logging
import json
import re
from typing import Dict, Optional
import nltk
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.summarizers.luhn import LuhnSummarizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words
from app.config import settings

#Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArticleSummarizer:

    def __init__(self):
        self.openai_available = bool(settings.OPENAI_API_KEY)
        self.sumy_initialized = False
        self.language = "english"
        self.openai_client = None

        if self.openai_available:
            try:
                #Initialize OpenAI client
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("OpenAI client initialized successfully (v1.0+)")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.openai_available = False
        else:
            logger.info("No OpenAI API key found, using Sumy summarization")

        self._init_sumy()

    def _init_sumy(self):
        try:
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                logger.info("Downloading NLTK punkt tokenizer...")
                nltk.download('punkt', quiet=True)

            try:
                nltk.data.find('corpora/stopwords')
            except LookupError:
                logger.info("Downloading NLTK stopwords...")
                nltk.download('stopwords', quiet=True)

            self.stemmer = Stemmer(self.language)
            self.stop_words = get_stop_words(self.language)

            self.summarizers = {
                'textrank': TextRankSummarizer(self.stemmer),
                'lexrank': LexRankSummarizer(self.stemmer),
                'luhn': LuhnSummarizer(self.stemmer),
                'lsa': LsaSummarizer(self.stemmer)
            }

            for summarizer in self.summarizers.values():
                summarizer.stop_words = self.stop_words

            self.sumy_initialized = True
            logger.info("Sumy summarizers initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Sumy: {e}")
            self.sumy_initialized = False

    def clean_text_for_summarization(self, text: str) -> str:
        if not text:
            return ""

        #Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text)

        text = re.sub(r'(Advertisement|ADVERTISEMENT)', '', text)
        text = re.sub(r'(Read more|READ MORE)', '', text)
        text = re.sub(r'(Subscribe|SUBSCRIBE)', '', text)

        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)

        return text.strip()

    def create_heading_from_text(self, text: str, original_title: str = "") -> str:
        if original_title and len(original_title) > 10:
            #Using original title, truncated if too long
            heading = original_title[:80].strip()
            if len(original_title) > 80:
                #Find last complete word
                last_space = heading.rfind(' ')
                if last_space > 40:
                    heading = heading[:last_space] + "..."
        else:
            #Extract first meaningful sentence
            sentences = re.split(r'[.!?]', text)
            heading = sentences[0][:80].strip() if sentences else "News Update"
            if len(sentences[0]) > 80:
                heading += "..."

        return heading

    def summarize_with_openai(self, article_text: str, title: str) -> Optional[Dict]:
        if not self.openai_client:
            return None

        try:
            #Limit article length to avoid token limits
            max_chars = 8000
            if len(article_text) > max_chars:
                article_text = article_text[:max_chars] + "..."

            system_prompt = (
                "You are a helpful summarization assistant. Produce a compact headline "
                "(6–10 words) and a 3–5 sentence summary. Return ONLY valid JSON with "
                'keys: "heading" and "summary". Avoid metadata, author names, and dates.'
            )

            user_prompt = f"""Article text:
---
{article_text}
---
Constraints:
- Heading: short, 6 to 10 words.
- Summary: 3 to 5 sentences, concise, no filler.
- Output JSON only: {{"heading": "...", "summary": "..."}}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )

            result_text = response.choices[0].message.content.strip()

            #Parse JSON response
            try:
                result = json.loads(result_text)
                if 'heading' in result and 'summary' in result:
                    logger.info(f"Successfully summarized with OpenAI: {result['heading']}")
                    return result
                else:
                    raise ValueError("Missing required keys in response")
            except json.JSONDecodeError:
                logger.error(f"Failed to parse OpenAI JSON response: {result_text}")
                return {
                    "heading": title[:60] if title else "News Update",
                    "summary": result_text[:500] if result_text else "Summary not available."
                }

        except Exception as e:
            logger.error(f"OpenAI summarization failed: {e}")
            return None

    def summarize_with_sumy(self, article_text: str, title: str, 
                           algorithm: str = 'textrank', num_sentences: int = 4) -> Optional[Dict]:
        if not self.sumy_initialized:
            logger.error("Sumy not initialized")
            return None

        try:
            #Clean the text
            cleaned_text = self.clean_text_for_summarization(article_text)

            if len(cleaned_text.split()) < 20:
                logger.warning("Text too short for meaningful summarization")
                return {
                    "heading": self.create_heading_from_text(cleaned_text, title),
                    "summary": cleaned_text[:300] + ("..." if len(cleaned_text) > 300 else "")
                }

            parser = PlaintextParser.from_string(cleaned_text, Tokenizer(self.language))

            summarizer = self.summarizers.get(algorithm, self.summarizers['textrank'])

            #Generate summary
            summary_sentences = summarizer(parser.document, num_sentences)

            summary_text = ' '.join([str(sentence) for sentence in summary_sentences])

            #Create heading
            heading = self.create_heading_from_text(cleaned_text, title)

            result = {
                "heading": heading,
                "summary": summary_text
            }

            logger.info(f"Successfully summarized with Sumy ({algorithm}): {heading[:50]}...")
            return result

        except Exception as e:
            logger.error(f"Sumy summarization failed: {e}")
            return None

    def summarize_text(self, article_text: str, title: str = "") -> Dict:
        if not article_text or len(article_text.strip()) < 50:
            return {
                "heading": title[:60] if title else "News Update",
                "summary": "Content too short to summarize effectively."
            }

        #OpenAI if available
        if self.openai_available and self.openai_client:
            result = self.summarize_with_openai(article_text, title)
            if result:
                return result
            else:
                logger.warning("OpenAI failed, falling back to Sumy")

        #Sumy with TextRank
        result = self.summarize_with_sumy(article_text, title, 'textrank')
        if result:
            return result

        #Alternative Sumy algorithm
        result = self.summarize_with_sumy(article_text, title, 'lexrank')
        if result:
            return result

        #Simple text truncation
        logger.warning("All summarization methods failed, using simple truncation")
        sentences = re.split(r'[.!?]+', article_text)

        #Take first few meaningful sentences
        meaningful_sentences = [s.strip() for s in sentences if len(s.strip()) > 20][:4]
        summary = '. '.join(meaningful_sentences)

        if not summary.endswith('.'):
            summary += '.'

        return {
            "heading": self.create_heading_from_text(article_text, title),
            "summary": summary[:500] + ("..." if len(summary) > 500 else "")
        }

    def get_available_algorithms(self) -> list:
        if self.sumy_initialized:
            return list(self.summarizers.keys())
        return []

'''
    def test_summarization(self, test_text: str = None) -> Dict:
        """Test summarization with sample text"""
        if not test_text:
            test_text = """
            The Indian Express is an English-language Indian daily newspaper founded in 1932. 
            It is published in Mumbai, Delhi, Pune, Ahmedabad, Chandigarh, Patna, Kochi, Lucknow, 
            Hyderabad, Bhopal, Madurai, Coimbatore, Visakhapatnam, Thiruvananthapuram and Nagpur. 
            The Indian Express Group also publishes several Hindi newspapers including Jansatta 
            and Loksatta. The group is known for its investigative journalism and has won 
            several national and international awards for its reporting.
            """

        return self.summarize_text(test_text.strip(), "Test Article: The Indian Express")
'''

#Global summarizer instance
summarizer = ArticleSummarizer()
