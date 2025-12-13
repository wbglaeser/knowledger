import random
import json
from database import Ibit

def generate_ai_quiz_question(session, openai_client):
    """
    Generate a multiple-choice quiz question using OpenAI.
    Picks a random ibit and asks OpenAI to create a question with 4 answer options.
    Returns a dict with the ibit, question, choices, and correct answer index.
    """
    if not openai_client:
        return None
    
    # Get all ibits
    ibits = session.query(Ibit).all()
    
    if not ibits:
        return None
    
    # Select a random ibit
    selected_ibit = random.choice(ibits)
    
    try:
        prompt = f"""Based on this information, create a multiple-choice quiz question:

Information: {selected_ibit.text}

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
            'ibit_id': selected_ibit.id,
            'ibit_text': selected_ibit.text,
            'question_text': quiz_data['question'],
            'choices': options,
            'correct_index': new_correct_index
        }
    except Exception as e:
        print(f"Error generating AI quiz: {e}")
        return None

def generate_quiz_question(session, num_choices=4):
    """
    Generate a multiple-choice quiz question from a random ibit.
    Returns a dict with the question, choices, and correct answer index.
    """
    # Get all ibits
    ibits = session.query(Ibit).all()
    
    if len(ibits) < num_choices:
        return None  # Not enough ibits to generate a quiz
    
    # Select a random ibit as the correct answer
    correct_ibit = random.choice(ibits)
    
    # Select random incorrect ibits
    other_ibits = [i for i in ibits if i.id != correct_ibit.id]
    incorrect_ibits = random.sample(other_ibits, min(num_choices - 1, len(other_ibits)))
    
    # Combine and shuffle choices
    all_choices = [correct_ibit] + incorrect_ibits
    random.shuffle(all_choices)
    
    # Find the index of the correct answer
    correct_index = all_choices.index(correct_ibit)
    
    # Create the question
    question = {
        'ibit_id': correct_ibit.id,
        'question_text': f"Which of these is a stored ibit?",
        'choices': [ibit.text[:100] + "..." if len(ibit.text) > 100 else ibit.text for ibit in all_choices],
        'correct_index': correct_index,
        'correct_answer': correct_ibit.text
    }
    
    return question

def generate_category_quiz(session, num_choices=4):
    """
    Generate a quiz asking which category an ibit belongs to.
    """
    # Get ibits that have categories
    ibits_with_cats = session.query(Ibit).filter(Ibit.categories.any()).all()
    
    if not ibits_with_cats:
        return None
    
    # Select a random ibit
    selected_ibit = random.choice(ibits_with_cats)
    correct_category = random.choice(selected_ibit.categories)
    
    # Get other categories for incorrect choices
    from database import Category
    all_categories = session.query(Category).all()
    
    if len(all_categories) < num_choices:
        return None
    
    other_categories = [c for c in all_categories if c.id != correct_category.id]
    incorrect_categories = random.sample(other_categories, min(num_choices - 1, len(other_categories)))
    
    # Combine and shuffle
    all_choices = [correct_category] + incorrect_categories
    random.shuffle(all_choices)
    correct_index = all_choices.index(correct_category)
    
    question = {
        'ibit_id': selected_ibit.id,
        'question_text': f"What category does this ibit belong to?\n\n\"{selected_ibit.text[:150]}...\"" if len(selected_ibit.text) > 150 else f"What category does this ibit belong to?\n\n\"{selected_ibit.text}\"",
        'choices': [cat.name for cat in all_choices],
        'correct_index': correct_index,
        'correct_answer': correct_category.name
    }
    
    return question

def generate_entity_quiz(session, num_choices=4):
    """
    Generate a quiz asking which entity is associated with an ibit.
    """
    # Get ibits that have entities
    ibits_with_entities = session.query(Ibit).filter(Ibit.entities.any()).all()
    
    if not ibits_with_entities:
        return None
    
    # Select a random ibit
    selected_ibit = random.choice(ibits_with_entities)
    correct_entity = random.choice(selected_ibit.entities)
    
    # Get other entities for incorrect choices
    from database import Entity
    all_entities = session.query(Entity).all()
    
    if len(all_entities) < num_choices:
        return None
    
    other_entities = [e for e in all_entities if e.id != correct_entity.id]
    incorrect_entities = random.sample(other_entities, min(num_choices - 1, len(other_entities)))
    
    # Combine and shuffle
    all_choices = [correct_entity] + incorrect_entities
    random.shuffle(all_choices)
    correct_index = all_choices.index(correct_entity)
    
    question = {
        'ibit_id': selected_ibit.id,
        'question_text': f"Which entity is associated with this ibit?\n\n\"{selected_ibit.text[:150]}...\"" if len(selected_ibit.text) > 150 else f"Which entity is associated with this ibit?\n\n\"{selected_ibit.text}\"",
        'choices': [ent.name for ent in all_choices],
        'correct_index': correct_index,
        'correct_answer': correct_entity.name
    }
    
    return question
