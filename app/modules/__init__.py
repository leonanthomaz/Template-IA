# src/modules/__init__.py

# Controllers
from app.modules.assistente.controllers.assistente_controller import AssistenteController

def register_routes(app):
    # Rotas
    app.include_router(AssistenteController(), prefix="/api/assistente", tags=["Rota Assistente"])
 
  
