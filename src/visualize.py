import networkx as nx
import matplotlib.pyplot as plt
from database import init_db, Ibit, Category, Entity

def visualize_knowledge_graph(output_file="knowledge_graph.png"):
    """
    Create a visual representation of the knowledge graph showing ibits, categories, and entities.
    """
    DBSession = init_db()
    session = DBSession()
    
    # Create a new graph
    G = nx.Graph()
    
    # Fetch all data
    ibits = session.query(Ibit).all()
    categories = session.query(Category).all()
    entities = session.query(Entity).all()
    
    # Add nodes
    for ibit in ibits:
        G.add_node(f"I{ibit.id}", type="ibit", label=ibit.text[:30] + "...")
    
    for category in categories:
        G.add_node(f"C_{category.name}", type="category", label=category.name)
    
    for entity in entities:
        G.add_node(f"E_{entity.name}", type="entity", label=entity.name)
    
    # Add edges
    for ibit in ibits:
        for category in ibit.categories:
            G.add_edge(f"I{ibit.id}", f"C_{category.name}")
        for entity in ibit.entities:
            G.add_edge(f"I{ibit.id}", f"E_{entity.name}")
    
    session.close()
    
    # Create visualization
    plt.figure(figsize=(20, 16))
    pos = nx.spring_layout(G, k=2, iterations=50)
    
    # Separate nodes by type
    ibit_nodes = [node for node, data in G.nodes(data=True) if data.get('type') == 'ibit']
    category_nodes = [node for node, data in G.nodes(data=True) if data.get('type') == 'category']
    entity_nodes = [node for node, data in G.nodes(data=True) if data.get('type') == 'entity']
    
    # Draw nodes with different colors
    nx.draw_networkx_nodes(G, pos, nodelist=ibit_nodes, node_color='lightblue', 
                          node_size=3000, alpha=0.8, label='Ibits')
    nx.draw_networkx_nodes(G, pos, nodelist=category_nodes, node_color='lightgreen', 
                          node_size=2000, alpha=0.8, label='Categories')
    nx.draw_networkx_nodes(G, pos, nodelist=entity_nodes, node_color='lightcoral', 
                          node_size=2000, alpha=0.8, label='Entities')
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, alpha=0.3)
    
    # Draw labels
    labels = {node: data['label'] for node, data in G.nodes(data=True)}
    nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight='bold')
    
    plt.title("Knowledge Graph", fontsize=16, fontweight='bold')
    plt.legend(scatterpoints=1, fontsize=12)
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Graph saved to {output_file}")
    plt.close()

if __name__ == "__main__":
    visualize_knowledge_graph()
