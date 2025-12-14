from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from database import init_db, Ibit, Category, Entity, Date
from pyvis.network import Network
from dotenv import load_dotenv
from openai import OpenAI
import secrets
import os

load_dotenv()

app = FastAPI(title="Knowledger Database UI")
templates = Jinja2Templates(directory="templates")
security = HTTPBasic()

DBSession = init_db()

# Load credentials from environment
WEB_USERNAME = os.getenv("WEB_USERNAME", "admin")
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "changeme")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify HTTP Basic Auth credentials"""
    correct_username = secrets.compare_digest(credentials.username, WEB_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, WEB_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, username: str = Depends(verify_credentials)):
    session = DBSession()
    try:
        ibits = session.query(Ibit).order_by(Ibit.date_added.desc()).all()
        categories = session.query(Category).order_by(Category.name).all()
        # Only show non-alias entities
        entities = session.query(Entity).filter(Entity.linked_to_id == None).order_by(Entity.name).all()
        dates = session.query(Date).order_by(Date.date.desc()).all()
        
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
            "dates": dates
        })
    finally:
        session.close()

@app.get("/ibits", response_class=HTMLResponse)
async def list_ibits(request: Request, username: str = Depends(verify_credentials)):
    session = DBSession()
    try:
        ibits = session.query(Ibit).order_by(Ibit.date_added.desc()).all()
        return templates.TemplateResponse("ibits.html", {
            "request": request,
            "ibits": ibits
        })
    finally:
        session.close()

@app.get("/ibits/{ibit_id}", response_class=HTMLResponse)
async def view_ibit(request: Request, ibit_id: int, username: str = Depends(verify_credentials)):
    session = DBSession()
    try:
        ibit = session.query(Ibit).filter_by(id=ibit_id).first()
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
    username: str = Depends(verify_credentials)
):
    session = DBSession()
    try:
        ibit = session.query(Ibit).filter_by(id=ibit_id).first()
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
                    category = session.query(Category).filter_by(name=cat_name).first()
                    if not category:
                        category = Category(name=cat_name)
                        session.add(category)
                    ibit.categories.append(category)
        
        # Add new entities
        if entities.strip():
            for ent_name in entities.split(","):
                ent_name = ent_name.strip()
                if ent_name:
                    entity = session.query(Entity).filter_by(name=ent_name).first()
                    if not entity:
                        entity = Entity(name=ent_name)
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
    username: str = Depends(verify_credentials)
):
    """Delete an ibit"""
    session = DBSession()
    try:
        ibit = session.query(Ibit).filter_by(id=ibit_id).first()
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
async def list_categories(request: Request, username: str = Depends(verify_credentials)):
    session = DBSession()
    try:
        categories = session.query(Category).order_by(Category.name).all()
        return templates.TemplateResponse("categories.html", {
            "request": request,
            "categories": categories
        })
    finally:
        session.close()

@app.get("/categories/{category_name}", response_class=HTMLResponse)
async def view_category(request: Request, category_name: str, username: str = Depends(verify_credentials)):
    session = DBSession()
    try:
        category = session.query(Category).filter_by(name=category_name).first()
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
async def list_entities(request: Request, username: str = Depends(verify_credentials)):
    session = DBSession()
    try:
        # Only show entities that aren't aliases of other entities
        entities = session.query(Entity).filter(Entity.linked_to_id == None).order_by(Entity.name).all()
        return templates.TemplateResponse("entities.html", {
            "request": request,
            "entities": entities
        })
    finally:
        session.close()

@app.get("/entities/{entity_name}", response_class=HTMLResponse)
async def view_entity(request: Request, entity_name: str, username: str = Depends(verify_credentials)):
    session = DBSession()
    try:
        entity = session.query(Entity).filter_by(name=entity_name).first()
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
    username: str = Depends(verify_credentials)
):
    """Merge this entity into the target entity (makes this an alias of target)"""
    session = DBSession()
    try:
        source_entity = session.query(Entity).filter_by(name=entity_name).first()
        target = session.query(Entity).filter_by(name=target_entity).first()
        
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
async def list_dates(request: Request, username: str = Depends(verify_credentials)):
    session = DBSession()
    try:
        dates = session.query(Date).order_by(Date.date.desc()).all()
        return templates.TemplateResponse("dates.html", {
            "request": request,
            "dates": dates
        })
    finally:
        session.close()

@app.get("/dates/{date}", response_class=HTMLResponse)
async def view_date(request: Request, date: str, username: str = Depends(verify_credentials)):
    session = DBSession()
    try:
        date_obj = session.query(Date).filter_by(date=date).first()
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
async def view_source(request: Request, source: str, username: str = Depends(verify_credentials)):
    session = DBSession()
    try:
        ibits = session.query(Ibit).filter_by(source=source).all()
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
async def quiz_page(request: Request, username: str = Depends(verify_credentials)):
    return templates.TemplateResponse("quiz.html", {
        "request": request
    })

@app.get("/api/quiz")
async def get_quiz(username: str = Depends(verify_credentials)):
    from quiz import generate_ai_quiz_question
    session = DBSession()
    try:
        question = generate_ai_quiz_question(session, openai_client)
        if question:
            return question
        else:
            raise HTTPException(status_code=500, detail="Unable to generate quiz")
    finally:
        session.close()

@app.post("/api/quiz/answer")
async def check_quiz_answer(request: Request, username: str = Depends(verify_credentials)):
    data = await request.json()
    selected_index = data.get("selected_index")
    correct_index = data.get("correct_index")
    
    if selected_index == correct_index:
        return {"correct": True, "message": "✅ Correct! Well done!"}
    else:
        return {"correct": False, "message": f"❌ Incorrect. The correct answer was option {chr(65 + correct_index)}."}

@app.get("/graph", response_class=HTMLResponse)
async def graph_page(request: Request, username: str = Depends(verify_credentials)):
    return templates.TemplateResponse("graph.html", {
        "request": request
    })

@app.get("/generate-graph")
async def generate_graph(username: str = Depends(verify_credentials)):
    session = DBSession()
    try:
        # Create network
        net = Network(height="800px", width="100%", bgcolor="#ffffff", font_color="#333333")
        net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=150, spring_strength=0.001)
        
        # Fetch all data
        ibits = session.query(Ibit).all()
        categories = session.query(Category).all()
        # Only include entities that aren't aliases
        entities = session.query(Entity).filter(Entity.linked_to_id == None).all()
        dates = session.query(Date).all()
        
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

@app.get("/static/{file_path:path}")
async def serve_static(file_path: str, username: str = Depends(verify_credentials)):
    file_location = f"static/{file_path}"
    if os.path.exists(file_location) and os.path.isfile(file_location):
        return FileResponse(file_location)
    return {"error": "File not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
