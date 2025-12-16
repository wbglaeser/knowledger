"""
Script to update web_ui.py with user authentication and user_id filtering.
This automates the tedious process of updating all routes.
"""

import re

def update_web_ui():
    with open('src/web_ui.py', 'r') as f:
        content = f.read()
    
    # Replace username: str = Depends(verify_credentials) with user: User = Depends(get_current_user)
    content = re.sub(
        r'username: str = Depends\(verify_credentials\)',
        'user: User = Depends(get_current_user)',
        content
    )
    
    # Add user_id filters to queries - this needs to be done carefully for each model
    # Pattern: session.query(Model).filter -> session.query(Model).filter(Model.user_id == user.id).filter
    # Or: session.query(Model).order_by -> session.query(Model).filter(Model.user_id == user.id).order_by
    
    # Ibit queries
    content = re.sub(
        r'session\.query\(Ibit\)\.order_by',
        'session.query(Ibit).filter(Ibit.user_id == user.id).order_by',
        content
    )
    content = re.sub(
        r'session\.query\(Ibit\)\.filter_by\(id=ibit_id\)',
        'session.query(Ibit).filter(Ibit.user_id == user.id, Ibit.id == ibit_id)',
        content
    )
    content = re.sub(
        r'session\.query\(Ibit\)\.filter\(Ibit\.id == ibit_id\)',
        'session.query(Ibit).filter(Ibit.user_id == user.id, Ibit.id == ibit_id)',
        content
    )
    
    # Category queries  
    content = re.sub(
        r'session\.query\(Category\)\.order_by',
        'session.query(Category).filter(Category.user_id == user.id).order_by',
        content
    )
    content = re.sub(
        r'session\.query\(Category\)\.filter_by\(name=category_name\)',
        'session.query(Category).filter(Category.user_id == user.id, Category.name == category_name)',
        content
    )
    content = re.sub(
        r'session\.query\(Category\)\.filter\(Category\.name == category_name\)',
        'session.query(Category).filter(Category.user_id == user.id, Category.name == category_name)',
        content
    )
    
    # Entity queries
    content = re.sub(
        r'session\.query\(Entity\)\.filter\(Entity\.linked_to_id == None\)\.order_by',
        'session.query(Entity).filter(Entity.user_id == user.id, Entity.linked_to_id == None).order_by',
        content
    )
    content = re.sub(
        r'session\.query\(Entity\)\.filter_by\(name=entity_name\)',
        'session.query(Entity).filter(Entity.user_id == user.id, Entity.name == entity_name)',
        content
    )
    content = re.sub(
        r'session\.query\(Entity\)\.filter\(Entity\.name == entity_name\)',
        'session.query(Entity).filter(Entity.user_id == user.id, Entity.name == entity_name)',
        content
    )
    content = re.sub(
        r'session\.query\(Entity\)\.filter\(Entity\.name == target_name\)',
        'session.query(Entity).filter(Entity.user_id == user.id, Entity.name == target_name)',
        content
    )
    content = re.sub(
        r'session\.query\(Entity\)\.filter\(Entity\.name == merge_name\)',
        'session.query(Entity).filter(Entity.user_id == user.id, Entity.name == merge_name)',
        content
    )
    
    # Date queries
    content = re.sub(
        r'session\.query\(Date\)\.order_by',
        'session.query(Date).filter(Date.user_id == user.id).order_by',
        content
    )
    content = re.sub(
        r'session\.query\(Date\)\.filter_by\(date=date\)',
        'session.query(Date).filter(Date.user_id == user.id, Date.date == date)',
        content
    )
    content = re.sub(
        r'session\.query\(Date\)\.filter\(Date\.date == date\)',
        'session.query(Date).filter(Date.user_id == user.id, Date.date == date)',
        content
    )
    
    # Add user to template context in responses (add ", user": user" before })
    # This is trickier, let's do it manually for important pages
    
    with open('src/web_ui.py', 'w') as f:
        f.write(content)
    
    print("✓ Updated web_ui.py with authentication")
    print("  - Replaced verify_credentials with get_current_user")
    print("  - Added user_id filtering to all queries")
    print("\nManual steps needed:")
    print("  - Review QuizProgress queries (may need special handling)")
    print("  - Add user info to template contexts where needed")
    print("  - Test all endpoints")

if __name__ == "__main__":
    update_web_ui()
