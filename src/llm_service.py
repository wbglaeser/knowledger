import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def extract_metadata_with_ai(ibit_text, existing_categories, openai_client):
    """Use OpenAI to extract categories, entities, dates, and source from ibit text"""
    if not openai_client:
        return None
    
    try:
        import json
        category_list = ", ".join(existing_categories) if existing_categories else "None yet"
        
        prompt = f"""You are a knowledge extraction assistant. Analyze the following information and extract metadata.

Existing categories: {category_list}

Information: {ibit_text}

Extract:
1. Categories (1-3 relevant topics):
   - ONLY use an existing category if it's a VERY CLOSE semantic match
   - If no existing category is highly similar, create a NEW category name
   - Use lowercase, 1-3 words each
   - Be specific and avoid overly broad categories
2. Entities (people, places, organizations, concepts - important nouns)
3. Dates (in YYYY-MM-DD, YYYY-MM, or YYYY format if mentioned):
   - ALWAYS use the MOST PRECISE date format available
   - If a full date (YYYY-MM-DD) is mentioned, ONLY include that - do NOT also include the year or month
   - If only month and year (YYYY-MM) are mentioned, ONLY include that - do NOT also include the year
   - Example: For "November 9, 1989" -> ["1989-11-09"] NOT ["1989-11-09", "1989-11", "1989"]
4. Source (if the text mentions where this information came from)

Respond with ONLY valid JSON in this exact format:
{{
  "categories": ["category1", "category2"],
  "entities": ["Entity1", "Entity2"],
  "dates": ["2024-01-01"],
  "source": "source name or url"
}}

If any field has no data, use an empty array [] or null for source."""

        response = openai_client.chat.completions.create(
            model="gpt-5.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        content = response.choices[0].message.content.strip()
        
        # Try to extract JSON if wrapped in code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        metadata = json.loads(content)
        return metadata
    except Exception as e:
        logger.error(f"Error extracting metadata with AI: {e}")
        return None
    
def transcribe_audio_with_ai(audio_file_path, openai_client):
    """Use OpenAI to transcribe audio file to text"""
    if not openai_client:
        return None
    
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio_file,
                response_format="text"
            )
        return transcript
    except Exception as e:
        logger.error(f"Error transcribing audio with AI: {e}")
        return None

def generate_quiz_question_with_ai(ibit_text, openai_client):
    """
    Generate a multiple-choice quiz question using OpenAI.
    Takes an ibit text and asks OpenAI to create a question with 4 answer options.
    Returns a dict with the question, options, and correct answer index.
    """
    if not openai_client:
        return None
    
    try:
        import json
        import random
        
        prompt = f"""Based on this information, create a multiple-choice quiz question:

Information: {ibit_text}

Create a question that tests knowledge about this information. Provide:
1. A clear question
2. Four answer options (A, B, C, D)
3. Only ONE option should be correct
4. Make the incorrect options plausible but clearly wrong

Respond ONLY with valid JSON in this exact format:
{{
  "question": "Your question here?",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correct_index": 0
}}

The correct_index should be 0, 1, 2, or 3 indicating which option is correct."""

        response = openai_client.chat.completions.create(
            model="gpt-5.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        content = response.choices[0].message.content.strip()
        
        # Try to extract JSON if wrapped in code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        quiz_data = json.loads(content)
        
        # Shuffle the answer options to avoid patterns
        options = quiz_data['options']
        correct_answer = options[quiz_data['correct_index']]
        
        # Shuffle options
        random.shuffle(options)
        
        # Find new index of correct answer
        new_correct_index = options.index(correct_answer)
        
        return {
            'question_text': quiz_data['question'],
            'choices': options,
            'correct_index': new_correct_index
        }
    except Exception as e:
        logger.error(f"Error generating AI quiz: {e}")
        return None