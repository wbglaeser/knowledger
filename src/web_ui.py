from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Cookie, Response
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from src.database import init_db, Ibit, Category, Entity, Date, User, QuizProgress
from pyvis.network import Network
from dotenv import load_dotenv
from openai import OpenAI
from typing import Optional
from src import auth
import os

load_dotenv()

app = FastAPI(title="Knowledger Database UI")

# Trust proxy headers for HTTPS detection
class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Trust X-Forwarded-Proto header from nginx
        if "x-forwarded-proto" in request.headers:
            request.scope["scheme"] = request.headers["x-forwarded-proto"]
        response = await call_next(request)
        return response

app.add_middleware(ProxyHeadersMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DBSession = init_db()

# Load credentials from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Custom exception for redirecting to login
class AuthRedirectException(Exception):
    pass

# Exception handler to redirect unauthenticated users to login
@app.exception_handler(AuthRedirectException)
async def auth_redirect_handler(request: Request, exc: AuthRedirectException):
    return RedirectResponse(url="/login", status_code=302)

# Authentication dependency
def get_current_user(request: Request, session_token: Optional[str] = Cookie(None)) -> User:
    """Get current user from session token cookie, redirect to login if not authenticated."""
    if not session_token:
        raise AuthRedirectException()
    
    db = DBSession()
    try:
        user = auth.get_user_from_token(db, session_token)
        if not user:
            raise AuthRedirectException()
        return user
    finally:
        db.close()

# Optional authentication for pages that can work with or without login
def get_current_user_optional(session_token: Optional[str] = Cookie(None)) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    if not session_token:
        return None
    
    db = DBSession()
    try:
        return auth.get_user_from_token(db, session_token)
    finally:
        db.close()

# Authentication endpoints
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: Optional[User] = Depends(get_current_user_optional)):
    """Show login page or redirect if already logged in."""
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    """Authenticate user and set session cookie."""
    db = DBSession()
    try:
        user = auth.authenticate_user(db, email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Create JWT token
        token = auth.create_access_token(data={"sub": str(user.id)})
        
        # Set cookie and redirect
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            max_age=60 * 60 * 24 * 7,  # 7 days
            samesite="lax"
        )
        return response
    finally:
        db.close()

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request, user: Optional[User] = Depends(get_current_user_optional)):
    """Show signup page or redirect if already logged in."""
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def signup(email: str = Form(...), password: str = Form(...), password_confirm: str = Form(...)):
    """Create new user account."""
    if password != password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    
    db = DBSession()
    try:
        user = auth.create_user(db, email, password)
        
        # Create JWT token
        token = auth.create_access_token(data={"sub": str(user.id)})
        
        # Set cookie and redirect
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            max_age=60 * 60 * 24 * 7,  # 7 days
            samesite="lax"
        )
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    finally:
        db.close()

@app.get("/logout")
async def logout():
    """Logout user by clearing session cookie."""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="session_token")
    return response

@app.get("/account", response_class=HTMLResponse)
async def account_page(request: Request, user: User = Depends(get_current_user)):
    """Account settings page with Telegram linking."""
    return templates.TemplateResponse("account.html", {
        "request": request,
        "user": user
    })

@app.post("/account/generate-code")
async def generate_linking_code(user: User = Depends(get_current_user)):
    """Generate a new Telegram linking code for the user."""
    db = DBSession()
    try:
        code = auth.create_linking_code(db, user.id)
        return JSONResponse({"code": code})
    finally:
        db.close()

@app.post("/account/delete")
async def delete_account(user: User = Depends(get_current_user)):
    """Delete user account and all associated data."""
    db = DBSession()
    try:
        # Delete all user data (cascading)
        db.query(QuizProgress).filter(QuizProgress.user_id == user.id).delete()
        
        # Delete many-to-many relationships for ibits
        for ibit in db.query(Ibit).filter(Ibit.user_id == user.id).all():
            ibit.categories.clear()
            ibit.entities.clear()
            ibit.dates.clear()
        
        # Delete main entities
        db.query(Ibit).filter(Ibit.user_id == user.id).delete()
        db.query(Category).filter(Category.user_id == user.id).delete()
        db.query(Entity).filter(Entity.user_id == user.id).delete()
        db.query(Date).filter(Date.user_id == user.id).delete()
        
        # Finally delete the user
        db.query(User).filter(User.id == user.id).delete()
        db.commit()
        
        # Clear session and redirect to signup
        response = RedirectResponse(url="/signup", status_code=302)
        response.delete_cookie(key="session_token")
        return response
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}"
        )
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user: User = Depends(get_current_user_optional)):
    # Show landing page if not logged in
    if not user:
        return templates.TemplateResponse("landing.html", {"request": request})
    
    session = DBSession()
    try:
        # Filter all data by user_id
        ibits = session.query(Ibit).filter(Ibit.user_id == user.id).order_by(Ibit.date_added.desc()).all()
        categories = session.query(Category).filter(Category.user_id == user.id).order_by(Category.name).all()
        # Only show non-alias entities
        entities = session.query(Entity).filter(Entity.user_id == user.id, Entity.linked_to_id == None).order_by(Entity.name).all()
        dates = session.query(Date).filter(Date.user_id == user.id).order_by(Date.date.desc()).all()
        
        # Get unique sources
        sources_dict = {}
        for ibit in ibits:
            if ibit.source:
                if ibit.source not in sources_dict:
                    sources_dict[ibit.source] = []
                sources_dict[ibit.source].append(ibit)
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "ibits": ibits,
            "categories": categories,
            "entities": entities,
            "sources": sources_dict,
            "dates": dates,
            "user": user
        })
    finally:
        session.close()

@app.get("/ibits", response_class=HTMLResponse)
async def list_ibits(request: Request, user: User = Depends(get_current_user)):
    session = DBSession()
    try:
        ibits = session.query(Ibit).filter(Ibit.user_id == user.id).order_by(Ibit.date_added.desc()).all()
        return templates.TemplateResponse("ibits.html", {
            "request": request,
            "ibits": ibits
        })
    finally:
        session.close()

@app.get("/ibits/{ibit_id}", response_class=HTMLResponse)
async def view_ibit(request: Request, ibit_id: int, user: User = Depends(get_current_user)):
    session = DBSession()
    try:
        ibit = session.query(Ibit).filter(Ibit.user_id == user.id, Ibit.id == ibit_id).first()
        if not ibit:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "message": f"Ibit with ID {ibit_id} not found"
            })
        return templates.TemplateResponse("ibit_detail.html", {
            "request": request,
            "ibit": ibit
        })
    finally:
        session.close()

@app.post("/ibits/{ibit_id}/edit")
async def edit_ibit(
    ibit_id: int,
    text: str = Form(...),
    source: str = Form(""),
    categories: str = Form(""),
    entities: str = Form(""),
    dates: str = Form(""),
    user: User = Depends(get_current_user)
):
    session = DBSession()
    try:
        ibit = session.query(Ibit).filter(Ibit.user_id == user.id, Ibit.id == ibit_id).first()
        if not ibit:
            return RedirectResponse(url="/", status_code=303)
        
        # Update text and source
        ibit.text = text.strip()
        ibit.source = source.strip() if source.strip() else None
        
        # Clear existing relationships
        ibit.categories.clear()
        ibit.entities.clear()
        ibit.dates.clear()
        
        # Add new categories
        if categories.strip():
            for cat_name in categories.split(","):
                cat_name = cat_name.strip().lower()
                if cat_name:
                    category = session.query(Category).filter(Category.name == cat_name, Category.user_id == user.id).first()
                    if not category:
                        category = Category(name=cat_name, user_id=user.id)
                        session.add(category)
                    ibit.categories.append(category)
        
        # Add new entities
        if entities.strip():
            for ent_name in entities.split(","):
                ent_name = ent_name.strip()
                if ent_name:
                    entity = session.query(Entity).filter(Entity.name == ent_name, Entity.user_id == user.id).first()
                    if not entity:
                        entity = Entity(name=ent_name, user_id=user.id)
                        session.add(entity)
                    ibit.entities.append(entity)
        
        # Add new dates
        if dates.strip():
            for date_str in dates.split(","):
                date_str = date_str.strip()
                if date_str:
                    date_obj = session.query(Date).filter_by(date=date_str).first()
                    if not date_obj:
                        date_obj = Date(date=date_str)
                        session.add(date_obj)
                    ibit.dates.append(date_obj)
        
        session.commit()
        return RedirectResponse(url=f"/ibits/{ibit_id}", status_code=303)
    except Exception as e:
        session.rollback()
        return templates.TemplateResponse("error.html", {
            "request": {},
            "message": f"Error updating ibit: {e}"
        })
    finally:
        session.close()

@app.post("/ibits/{ibit_id}/delete")
async def delete_ibit(
    ibit_id: int,
    user: User = Depends(get_current_user)
):
    """Delete an ibit"""
    session = DBSession()
    try:
        ibit = session.query(Ibit).filter(Ibit.user_id == user.id, Ibit.id == ibit_id).first()
        if not ibit:
            return templates.TemplateResponse("error.html", {
                "request": {},
                "message": f"Ibit with ID {ibit_id} not found"
            })
        
        session.delete(ibit)
        session.commit()
        return RedirectResponse(url="/ibits", status_code=303)
    except Exception as e:
        session.rollback()
        return templates.TemplateResponse("error.html", {
            "request": {},
            "message": f"Error deleting ibit: {e}"
        })
    finally:
        session.close()

@app.get("/categories", response_class=HTMLResponse)
async def list_categories(request: Request, user: User = Depends(get_current_user)):
    session = DBSession()
    try:
        categories = session.query(Category).filter(Category.user_id == user.id).order_by(Category.name).all()
        return templates.TemplateResponse("categories.html", {
            "request": request,
            "categories": categories
        })
    finally:
        session.close()

@app.get("/categories/{category_name}", response_class=HTMLResponse)
async def view_category(request: Request, category_name: str, user: User = Depends(get_current_user)):
    session = DBSession()
    try:
        category = session.query(Category).filter(Category.user_id == user.id, Category.name == category_name).first()
        if not category:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "message": f"Category '{category_name}' not found"
            })
        return templates.TemplateResponse("category_detail.html", {
            "request": request,
            "category": category
        })
    finally:
        session.close()

@app.get("/entities", response_class=HTMLResponse)
async def list_entities(request: Request, user: User = Depends(get_current_user)):
    session = DBSession()
    try:
        # Only show entities that aren't aliases of other entities
        entities = session.query(Entity).filter(Entity.user_id == user.id, Entity.linked_to_id == None).order_by(Entity.name).all()
        return templates.TemplateResponse("entities.html", {
            "request": request,
            "entities": entities
        })
    finally:
        session.close()

@app.get("/entities/{entity_name}", response_class=HTMLResponse)
async def view_entity(request: Request, entity_name: str, user: User = Depends(get_current_user)):
    session = DBSession()
    try:
        entity = session.query(Entity).filter(Entity.user_id == user.id, Entity.name == entity_name).first()
        if not entity:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "message": f"Entity '{entity_name}' not found"
            })
        
        # Get all other entities (excluding this one and already linked entities)
        all_entities = session.query(Entity).filter(
            Entity.id != entity.id,
            Entity.linked_to_id == None  # Only show entities that aren't aliases of others
        ).order_by(Entity.name).all()
        
        # Get entities that are linked to this one (aliases)
        aliases = session.query(Entity).filter(Entity.linked_to_id == entity.id).all()
        
        return templates.TemplateResponse("entity_detail.html", {
            "request": request,
            "entity": entity,
            "all_entities": all_entities,
            "aliases": aliases
        })
    finally:
        session.close()

@app.post("/entities/{entity_name}/merge")
async def merge_entity(
    request: Request,
    entity_name: str,
    target_entity: str = Form(...),
    user: User = Depends(get_current_user)
):
    """Merge this entity into the target entity (makes this an alias of target)"""
    session = DBSession()
    try:
        source_entity = session.query(Entity).filter(Entity.user_id == user.id, Entity.name == entity_name).first()
        target = session.query(Entity).filter(Entity.name == target_entity, Entity.user_id == user.id).first()
        
        if not source_entity or not target:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "message": "Entity not found"
            })
        
        if source_entity.id == target.id:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "message": "Cannot merge an entity with itself"
            })
        
        # Transfer all ibits from source to target
        for ibit in source_entity.ibits:
            if target not in ibit.entities:
                ibit.entities.append(target)
            if source_entity in ibit.entities:
                ibit.entities.remove(source_entity)
        
        # Mark source as alias of target
        source_entity.linked_to_id = target.id
        
        session.commit()
        return RedirectResponse(url=f"/entities/{target_entity}", status_code=303)
    except Exception as e:
        session.rollback()
        return templates.TemplateResponse("error.html", {
            "request": request,
            "message": f"Error merging entities: {e}"
        })
    finally:
        session.close()

@app.get("/dates", response_class=HTMLResponse)
async def list_dates(request: Request, user: User = Depends(get_current_user)):
    session = DBSession()
    try:
        dates = session.query(Date).filter(Date.user_id == user.id).order_by(Date.date.desc()).all()
        return templates.TemplateResponse("dates.html", {
            "request": request,
            "dates": dates
        })
    finally:
        session.close()

@app.get("/dates/{date}", response_class=HTMLResponse)
async def view_date(request: Request, date: str, user: User = Depends(get_current_user)):
    session = DBSession()
    try:
        date_obj = session.query(Date).filter(Date.user_id == user.id, Date.date == date).first()
        if not date_obj:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "message": f"Date '{date}' not found"
            })
        return templates.TemplateResponse("date_detail.html", {
            "request": request,
            "date": date_obj
        })
    finally:
        session.close()

@app.get("/sources/{source:path}", response_class=HTMLResponse)
async def view_source(request: Request, source: str, user: User = Depends(get_current_user)):
    session = DBSession()
    try:
        ibits = session.query(Ibit).filter(Ibit.source == source, Ibit.user_id == user.id).all()
        if not ibits:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "message": f"No ibits found for source '{source}'"
            })
        return templates.TemplateResponse("source_detail.html", {
            "request": request,
            "source": source,
            "ibits": ibits
        })
    finally:
        session.close()

@app.get("/quiz", response_class=HTMLResponse)
async def quiz_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("quiz.html", {
        "request": request,
        "user": user
    })

@app.get("/api/quiz")
async def get_quiz(user: User = Depends(get_current_user)):
    from llm_service import generate_quiz_question_with_ai
    import random
    
    session = DBSession()
    try:
        if not openai_client:
            raise HTTPException(status_code=500, detail="OpenAI client not configured")
        
        # Get all ibit IDs for this user
        all_ibit_ids = [ibit.id for ibit in session.query(Ibit).filter(Ibit.user_id == user.id).all()]
        
        if not all_ibit_ids:
            raise HTTPException(status_code=500, detail="No ibits available for quiz")
        
        # Load user's quiz progress from database
        progress = session.query(QuizProgress).filter(QuizProgress.user_id == user.id).first()
        
        if not progress:
            # Create new progress entry
            progress = QuizProgress(user_id=user.id, username=user.email, used_ibit_ids="")
            session.add(progress)
            session.commit()
        
        # Parse used IDs
        used_ids = set()
        if progress.used_ibit_ids:
            used_ids = set(int(id_str) for id_str in progress.used_ibit_ids.split(",") if id_str)
        
        # Calculate remaining pool
        pool = set(all_ibit_ids) - used_ids
        
        # If pool is empty or ibits were added/removed, reset the cycle
        if not pool:
            used_ids = set()
            pool = set(all_ibit_ids)
        
        # Pick a random ibit from the pool
        selected_id = random.choice(list(pool))
        used_ids.add(selected_id)
        
        # Save progress back to database
        progress.used_ibit_ids = ",".join(str(id) for id in sorted(used_ids))
        session.commit()
        
        # Get the ibit and generate question
        selected_ibit = session.query(Ibit).filter(Ibit.user_id == user.id, Ibit.id == selected_id).first()
        quiz_data = generate_quiz_question_with_ai(selected_ibit.text, openai_client)
        
        if not quiz_data:
            raise HTTPException(status_code=500, detail="Failed to generate quiz question")
        
        quiz_data['ibit_id'] = selected_ibit.id
        quiz_data['ibit_text'] = selected_ibit.text
        quiz_data['progress'] = {
            'current': len(used_ids),
            'total': len(all_ibit_ids)
        }
        
        return quiz_data
        
    finally:
        session.close()

@app.post("/api/quiz/answer")
async def check_quiz_answer(request: Request, user: User = Depends(get_current_user)):
    data = await request.json()
    selected_index = data.get("selected_index")
    correct_index = data.get("correct_index")
    
    if selected_index == correct_index:
        return {"correct": True, "message": "✅ Correct! Well done!"}
    else:
        return {"correct": False, "message": f"❌ Incorrect. The correct answer was option {chr(65 + correct_index)}."}

@app.get("/graph", response_class=HTMLResponse)
async def graph_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("graph.html", {
        "request": request,
        "user": user
    })

@app.get("/generate-graph")
async def generate_graph(user: User = Depends(get_current_user)):
    session = DBSession()
    try:
        # Create network
        net = Network(height="800px", width="100%", bgcolor="#ffffff", font_color="#333333")
        net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=150, spring_strength=0.001)
        
        # Fetch all data for this user
        ibits = session.query(Ibit).filter(Ibit.user_id == user.id).all()
        categories = session.query(Category).filter(Category.user_id == user.id).all()
        # Only include entities that aren't aliases
        entities = session.query(Entity).filter(Entity.linked_to_id == None, Entity.user_id == user.id).all()
        dates = session.query(Date).filter(Date.user_id == user.id).all()
        
        # Calculate node sizes based on number of connections
        def calculate_size(base_size, connection_count):
            # Scale size based on connections: base_size + (connections * 3)
            return base_size + (connection_count * 3)
        
        # Add ibit nodes with dynamic sizing
        for ibit in ibits:
            label = ibit.text[:50] + "..." if len(ibit.text) > 50 else ibit.text
            wrapped_text = "\n".join([ibit.text[i:i+60] for i in range(0, len(ibit.text), 60)])
            # Count connections: categories + entities + dates + source (if exists)
            connection_count = len(ibit.categories) + len(ibit.entities) + len(ibit.dates) + (1 if ibit.source else 0)
            net.add_node(f"I{ibit.id}", 
                        label=f"Ibit {ibit.id}",
                        title=wrapped_text,
                        color="#87CEEB",
                        size=calculate_size(15, connection_count),
                        shape="dot")
        
        # Add category nodes with dynamic sizing
        for category in categories:
            connection_count = len(category.ibits)
            net.add_node(f"C_{category.name}",
                        label=f"#{category.name}",
                        title=f"Category: {category.name} ({connection_count} ibits)",
                        color="#90EE90",
                        size=calculate_size(15, connection_count),
                        shape="box")
        
        # Add entity nodes with dynamic sizing
        for entity in entities:
            connection_count = len(entity.ibits)
            net.add_node(f"E_{entity.name}",
                        label=f"@{entity.name}",
                        title=f"Entity: {entity.name} ({connection_count} ibits)",
                        color="#FFB6C1",
                        size=calculate_size(15, connection_count),
                        shape="diamond")
        
        # Add source nodes with dynamic sizing
        sources = set(ibit.source for ibit in ibits if ibit.source)
        for source in sources:
            connection_count = sum(1 for ibit in ibits if ibit.source == source)
            net.add_node(f"S_{source}",
                        label=f"&{source[:30]}..." if len(source) > 30 else f"&{source}",
                        title=f"Source: {source} ({connection_count} ibits)",
                        color="#FFD700",
                        size=calculate_size(15, connection_count),
                        shape="triangle")
        
        # Add date nodes with dynamic sizing
        for date in dates:
            connection_count = len(date.ibits)
            net.add_node(f"D_{date.date}",
                        label=f"^{date.date}",
                        title=f"Date: {date.date} ({connection_count} ibits)",
                        color="#FF8C00",
                        size=calculate_size(15, connection_count),
                        shape="star")
        
        # Add edges
        for ibit in ibits:
            for category in ibit.categories:
                net.add_edge(f"I{ibit.id}", f"C_{category.name}", color="#999")
            for entity in ibit.entities:
                net.add_edge(f"I{ibit.id}", f"E_{entity.name}", color="#999")
            if ibit.source:
                net.add_edge(f"I{ibit.id}", f"S_{ibit.source}", color="#999")
            for date in ibit.dates:
                net.add_edge(f"I{ibit.id}", f"D_{date.date}", color="#999")
        
        # Configure interaction options
        net.set_options("""
        var options = {
            "physics": {
                "barnesHut": {
                    "gravitationalConstant": -8000,
                    "centralGravity": 0.3,
                    "springLength": 150,
                    "springConstant": 0.001
                }
            },
            "interaction": {
                "navigationButtons": true,
                "keyboard": true
            }
        }
        """)
        
        # Save to static file
        os.makedirs("static", exist_ok=True)
        net.save_graph("static/graph.html")
        
        # Add custom CSS to remove margins and border
        with open("static/graph.html", "r") as f:
            content = f.read()
        
        # Remove the default border from pyvis
        content = content.replace("border: 1px solid lightgray;", "border: none;")
        
        # Inject custom CSS
        custom_css = """
        <style>
        body {
            margin: 0;
            padding: 0;
        }
        #mynetwork {
            border: none !important;
        }
        canvas {
            display: block;
        }
        </style>
        """
        content = content.replace("</head>", f"{custom_css}</head>")
        
        with open("static/graph.html", "w") as f:
            f.write(content)
        
        return {"status": "success", "graph_url": "/static/graph.html"}
    finally:
        session.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
