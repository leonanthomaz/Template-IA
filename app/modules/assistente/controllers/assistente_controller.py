# app/modules/assistente/controller/assistente_controller.py

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
import httpx
from app.core.config.settings import Configuration
from app.modules.assistente.models.groq_model import GroqChatRequest
from app.modules.assistente.services.assistente_service import AssistenteService
from app.shared.utils.retornar_timestamp import get_current_timestamp

class AssistenteController(APIRouter):
    """Controller para operações com Assistente"""
    
    def __init__(self):
        super().__init__()
        self.config = Configuration()
        self.logger = logging.getLogger(__name__)
        self.service = AssistenteService()

        # Health check
        self.add_api_route(
            path="/health",
            endpoint=self.health_check,
            methods=["GET"],
            summary="Health check"
        )
        
        # Chat
        self.add_api_route(
            path="/chat",
            endpoint=self.chat,
            methods=["POST"],
            summary="Envia mensagem para IA via Assistente"
        )
        
        self.add_api_route(
            path="/models",
            endpoint=self.list_models,
            methods=["GET"],
            summary="Lista modelos disponíveis no Groq"
        )
        
        # ============ MASTER ENDPOINTS ============
        self.add_api_route(
            path="/master",
            endpoint=self.get_master_config,
            methods=["GET"],
            summary="Obtém configuração master do sistema"
        )
        
        self.add_api_route(
            path="/master",
            endpoint=self.update_master_config,
            methods=["PUT"],
            summary="Atualiza configuração master"
        )
        
        # ============ USER ENDPOINTS ============
        self.add_api_route(
            path="/users",
            endpoint=self.get_users,
            methods=["GET"],
            summary="Lista todos os usuários"
        )
        
        self.add_api_route(
            path="/users",
            endpoint=self.create_user,
            methods=["POST"],
            summary="Cria um novo usuário"
        )
        
        self.add_api_route(
            path="/users/{user_id}",
            endpoint=self.get_user,
            methods=["GET"],
            summary="Obtém usuário por ID"
        )
        
        self.add_api_route(
            path="/users/{user_id}",
            endpoint=self.update_user,
            methods=["PUT"],
            summary="Atualiza um usuário"
        )
        
        self.add_api_route(
            path="/users/{user_id}",
            endpoint=self.delete_user,
            methods=["DELETE"],
            summary="Deleta/Desativa um usuário"
        )
        
        # ============ ASSISTANT ENDPOINTS ============
        self.add_api_route(
            path="/assistants",
            endpoint=self.get_assistants,
            methods=["GET"],
            summary="Lista todas as assistentes"
        )
        
        self.add_api_route(
            path="/assistants",
            endpoint=self.create_assistant,
            methods=["POST"],
            summary="Cria uma nova assistente"
        )
        
        self.add_api_route(
            path="/assistants/{assistant_id}",
            endpoint=self.get_assistant_by_id,
            methods=["GET"],
            summary="Obtém assistente por ID"
        )
        
        self.add_api_route(
            path="/assistants/{assistant_id}",
            endpoint=self.update_assistant,
            methods=["PUT"],
            summary="Atualiza configurações da assistente"
        )
        
        self.add_api_route(
            path="/assistants/{assistant_id}",
            endpoint=self.delete_assistant,
            methods=["DELETE"],
            summary="Deleta/Desativa uma assistente"
        )
        
        self.add_api_route(
            path="/assistants/default",
            endpoint=self.get_default_assistant,
            methods=["GET"],
            summary="Obtém assistente padrão"
        )
        
        self.add_api_route(
            path="/assistants/{assistant_id}/set-default",
            endpoint=self.set_default_assistant,
            methods=["POST"],
            summary="Define uma assistente como padrão"
        )
        
        self.add_api_route(
            path="/assistants/user/{user_id}",
            endpoint=self.get_assistant_by_user,
            methods=["GET"],
            summary="Obtém assistente de um usuário"
        )
    
    # ============ HEALTH ============
    def health_check(self) -> Dict[str, str]:
        return {
            "status": "ONLINE",
            "service": "API ASSISTENTE",
            "timestamp": get_current_timestamp()
        }
    
    async def chat(self, request: GroqChatRequest) -> Dict:
        """Endpoint principal para conversar com modelos Groq"""
        try:
            # Pega variáveis do .env
            api_key = self.config.groq_api_key
            default_model = self.config.groq_model or "llama-3.1-8b-instant"
            url = self.config.groq_url or "https://api.groq.com/openai/v1/chat/completions"
            
            model = request.model or default_model
            
            # Prepara payload no formato OpenAI (compatível com Groq)
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": request.message}
                ],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": request.stream
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            self.logger.info(f"Groq - Enviando requisição - Modelo: {model}")
            self.logger.debug(f"Payload: {payload}")
            
            # Faz a requisição
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
            
            # Extrai resposta (formato OpenAI)
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # Estatísticas de velocidade (Groq é famoso pela velocidade)
            usage = data.get("usage", {})
            speed_info = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "estimated_speed": "~560 tokens/seg" if "8b" in model.lower() else "~280 tokens/seg"
            }
            
            self.logger.info(f"Groq - Resposta recebida - {speed_info['total_tokens']} tokens")
            
            return {
                "success": True,
                "response": content,
                "model": model,
                "usage": speed_info,
                "timestamp": get_current_timestamp(),
                "provider": "groq"
            }
            
        except httpx.TimeoutException:
            self.logger.error("Groq - Timeout na requisição")
            raise HTTPException(status_code=504, detail="Tempo limite excedido")
        except httpx.HTTPStatusError as e:
            self.logger.error(f"Groq - Erro HTTP: {e.response.status_code}")
            error_detail = e.response.text
            try:
                error_json = e.response.json()
                error_detail = error_json.get("error", {}).get("message", str(e))
            except:
                pass
            raise HTTPException(
                status_code=e.response.status_code, 
                detail=f"Erro na API Groq: {error_detail}"
            )
        except Exception as e:
            self.logger.error(f"Groq - Erro inesperado: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def list_models(self) -> Dict:
        """Lista todos os modelos disponíveis no Groq"""
        try:
            api_key = self.config.groq_api_key
            url = "https://api.groq.com/openai/v1/models"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
            
            models = data.get("data", [])
            
            # Filtra e organiza modelos relevantes
            model_list = []
            for model in models:
                model_id = model.get("id", "")
                # Só mostra modelos que parecem úteis (filtra os de segurança)
                if any(keyword in model_id for keyword in ["llama", "gpt-oss", "qwen", "whisper"]):
                    model_list.append({
                        "id": model_id,
                        "created": model.get("created"),
                        "owned_by": model.get("owned_by", "groq")
                    })
            
            return {
                "success": True,
                "total_models": len(model_list),
                "models": model_list,
                "timestamp": get_current_timestamp()
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao listar modelos: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    # ============ MASTER METHODS ============
    async def get_master_config(self) -> Dict:
        """Obtém configuração master"""
        try:
            master = self.service.get_master_config()
            if master:
                return {
                    "success": True,
                    "data": {
                        "id": master.id,
                        "system_name": master.system_name,
                        "system_version": master.system_version,
                        "environment": master.environment,
                        "is_active": master.is_active,
                        "default_language": master.default_language,
                        "default_timezone": master.default_timezone,
                        "maintenance_mode": master.maintenance_mode,
                        "description": master.description,
                        "system_owner": master.system_owner,
                        "created_at": master.created_at.isoformat() if master.created_at else None,
                        "updated_at": master.updated_at.isoformat() if master.updated_at else None
                    }
                }
            return {"success": False, "message": "Configuração master não encontrada"}
        except Exception as e:
            self.logger.error(f"Erro ao obter master config: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def update_master_config(self, config_data: Dict[str, Any]) -> Dict:
        """Atualiza configuração master"""
        try:
            master = self.service.update_master_config(**config_data)
            if master:
                return {
                    "success": True,
                    "message": "Configuração master atualizada com sucesso",
                    "data": {
                        "id": master.id,
                        "system_name": master.system_name,
                        "system_version": master.system_version,
                        "environment": master.environment,
                        "maintenance_mode": master.maintenance_mode
                    }
                }
            return {"success": False, "message": "Configuração master não encontrada"}
        except Exception as e:
            self.logger.error(f"Erro ao atualizar master config: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ============ USER METHODS ============
    async def get_users(self, active_only: bool = True) -> Dict:
        """Lista todos os usuários"""
        try:
            users = self.service.get_all_users(active_only)
            return {
                "success": True,
                "total": len(users),
                "data": [
                    {
                        "id": u.id,
                        "username": u.username,
                        "email": u.email,
                        "full_name": u.full_name,
                        "is_active": u.is_active,
                        "is_admin": u.is_admin,
                        "created_at": u.created_at.isoformat() if u.created_at else None
                    } for u in users
                ]
            }
        except Exception as e:
            self.logger.error(f"Erro ao listar usuários: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def create_user(self, user_data: Dict[str, Any]) -> Dict:
        """Cria um novo usuário"""
        try:
            user = self.service.create_user(
                username=user_data.get('username'),
                email=user_data.get('email'),
                full_name=user_data.get('full_name'),
                **{k: v for k, v in user_data.items() if k not in ['username', 'email', 'full_name']}
            )
            return {
                "success": True,
                "message": "Usuário criado com sucesso",
                "data": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name
                }
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Erro ao criar usuário: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_user(self, user_id: int) -> Dict:
        """Obtém usuário por ID"""
        try:
            user = self.service.get_user_by_id(user_id)
            if user:
                return {
                    "success": True,
                    "data": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "full_name": user.full_name,
                        "preferred_language": user.preferred_language,
                        "timezone": user.timezone,
                        "is_active": user.is_active,
                        "is_admin": user.is_admin,
                        "bio": user.bio,
                        "created_at": user.created_at.isoformat() if user.created_at else None,
                        "updated_at": user.updated_at.isoformat() if user.updated_at else None
                    }
                }
            return {"success": False, "message": "Usuário não encontrado"}
        except Exception as e:
            self.logger.error(f"Erro ao obter usuário: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def update_user(self, user_id: int, user_data: Dict[str, Any]) -> Dict:
        """Atualiza um usuário"""
        try:
            user = self.service.update_user(user_id, **user_data)
            if user:
                return {
                    "success": True,
                    "message": "Usuário atualizado com sucesso",
                    "data": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "full_name": user.full_name
                    }
                }
            return {"success": False, "message": "Usuário não encontrado"}
        except Exception as e:
            self.logger.error(f"Erro ao atualizar usuário: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def delete_user(self, user_id: int, soft: bool = True) -> Dict:
        """Deleta/Desativa um usuário"""
        try:
            result = self.service.delete_user(user_id, soft_delete=soft)
            if result:
                return {
                    "success": True,
                    "message": f"Usuário {'desativado' if soft else 'deletado'} com sucesso"
                }
            return {"success": False, "message": "Usuário não encontrado"}
        except Exception as e:
            self.logger.error(f"Erro ao deletar usuário: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ============ ASSISTANT METHODS ============
    async def get_assistants(self, active_only: bool = True) -> Dict:
        """Lista todas as assistentes"""
        try:
            assistants = self.service.get_all_assistants(active_only)
            return {
                "success": True,
                "total": len(assistants),
                "data": [
                    {
                        "id": a.id,
                        "name": a.name,
                        "user_id": a.user_id,
                        "model": a.model,
                        "is_active": a.is_active,
                        "is_default": a.is_default,
                        "personality": a.personality,
                        "created_at": a.created_at.isoformat() if a.created_at else None
                    } for a in assistants
                ]
            }
        except Exception as e:
            self.logger.error(f"Erro ao listar assistentes: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def create_assistant(self, assistant_data: Dict[str, Any]) -> Dict:
        """Cria uma nova assistente"""
        try:
            assistant = self.service.create_assistant(
                user_id=assistant_data.get('user_id'),
                name=assistant_data.get('name'),
                **{k: v for k, v in assistant_data.items() if k not in ['user_id', 'name']}
            )
            return {
                "success": True,
                "message": "Assistente criada com sucesso",
                "data": {
                    "id": assistant.id,
                    "name": assistant.name,
                    "user_id": assistant.user_id,
                    "model": assistant.model
                }
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Erro ao criar assistente: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_assistant_by_id(self, assistant_id: int) -> Dict:
        """Obtém assistente por ID"""
        try:
            assistant = self.service.get_assistant_by_id(assistant_id)
            if assistant:
                return {
                    "success": True,
                    "data": {
                        "id": assistant.id,
                        "name": assistant.name,
                        "user_id": assistant.user_id,
                        "model": assistant.model,
                        "temperature": assistant.temperature,
                        "max_tokens": assistant.max_tokens,
                        "greeting_message": assistant.greeting_message,
                        "system_prompt": assistant.system_prompt,
                        "personality": assistant.personality,
                        "communication_style": assistant.communication_style,
                        "is_active": assistant.is_active,
                        "is_default": assistant.is_default,
                        "created_at": assistant.created_at.isoformat() if assistant.created_at else None,
                        "updated_at": assistant.updated_at.isoformat() if assistant.updated_at else None
                    }
                }
            return {"success": False, "message": "Assistente não encontrada"}
        except Exception as e:
            self.logger.error(f"Erro ao obter assistente: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_assistant_by_user(self, user_id: int) -> Dict:
        """Obtém assistente de um usuário"""
        try:
            assistant = self.service.get_assistant_by_user(user_id)
            if assistant:
                return {
                    "success": True,
                    "data": {
                        "id": assistant.id,
                        "name": assistant.name,
                        "model": assistant.model,
                        "temperature": assistant.temperature,
                        "greeting_message": assistant.greeting_message,
                        "personality": assistant.personality,
                        "communication_style": assistant.communication_style
                    }
                }
            return {"success": False, "message": "Assistente não encontrada para este usuário"}
        except Exception as e:
            self.logger.error(f"Erro ao obter assistente do usuário: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def update_assistant(self, assistant_id: int, assistant_data: Dict[str, Any]) -> Dict:
        """Atualiza configurações da assistente"""
        try:
            assistant = self.service.update_assistant(assistant_id, **assistant_data)
            if assistant:
                return {
                    "success": True,
                    "message": "Assistente atualizada com sucesso",
                    "data": {
                        "id": assistant.id,
                        "name": assistant.name,
                        "model": assistant.model
                    }
                }
            return {"success": False, "message": "Assistente não encontrada"}
        except Exception as e:
            self.logger.error(f"Erro ao atualizar assistente: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def delete_assistant(self, assistant_id: int, soft: bool = True) -> Dict:
        """Deleta/Desativa uma assistente"""
        try:
            result = self.service.delete_assistant(assistant_id, soft_delete=soft)
            if result:
                return {
                    "success": True,
                    "message": f"Assistente {'desativada' if soft else 'deletada'} com sucesso"
                }
            return {"success": False, "message": "Assistente não encontrada"}
        except Exception as e:
            self.logger.error(f"Erro ao deletar assistente: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_default_assistant(self) -> Dict:
        """Obtém assistente padrão"""
        try:
            assistant = self.service.get_default_assistant()
            if assistant:
                return {
                    "success": True,
                    "data": {
                        "id": assistant.id,
                        "name": assistant.name,
                        "user_id": assistant.user_id,
                        "model": assistant.model,
                        "greeting_message": assistant.greeting_message,
                        "personality": assistant.personality
                    }
                }
            return {"success": False, "message": "Assistente padrão não encontrada"}
        except Exception as e:
            self.logger.error(f"Erro ao obter assistente padrão: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def set_default_assistant(self, assistant_id: int) -> Dict:
        """Define uma assistente como padrão"""
        try:
            assistant = self.service.set_default_assistant(assistant_id)
            if assistant:
                return {
                    "success": True,
                    "message": "Assistente definida como padrão",
                    "data": {
                        "id": assistant.id,
                        "name": assistant.name
                    }
                }
            return {"success": False, "message": "Assistente não encontrada"}
        except Exception as e:
            self.logger.error(f"Erro ao definir assistente padrão: {e}")
            raise HTTPException(status_code=500, detail=str(e))