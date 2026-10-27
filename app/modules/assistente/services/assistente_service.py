# app/modules/assistente/service/assistente_service.py
import logging
from typing import Optional, List
from sqlmodel import select
from app.shared.database.connection import session_scope
from app.modules.assistente.models.database_models import Master, User, Assistant


class AssistenteService:
    """Serviço para operações com o assistente"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    # ============ MASTER ============
    def get_master_config(self) -> Optional[Master]:
        """Obtém a configuração master do sistema"""
        with session_scope() as session:
            return session.query(Master).first()
    
    def update_master_config(self, **kwargs) -> Optional[Master]:
        """Atualiza a configuração master"""
        with session_scope() as session:
            master = session.query(Master).first()
            if master:
                for key, value in kwargs.items():
                    if hasattr(master, key):
                        setattr(master, key, value)
                session.add(master)
                session.flush()
                session.refresh(master)
            return master
    
    # ============ USERS ============
    def get_all_users(self, active_only: bool = True) -> List[User]:
        """Lista todos os usuários"""
        with session_scope() as session:
            statement = select(User)
            if active_only:
                statement = statement.where(User.is_active == True)
            return session.exec(statement).all()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Obtém um usuário pelo ID"""
        with session_scope() as session:
            return session.get(User, user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Obtém um usuário pelo username"""
        with session_scope() as session:
            statement = select(User).where(User.username == username)
            return session.exec(statement).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Obtém um usuário pelo email"""
        with session_scope() as session:
            statement = select(User).where(User.email == email)
            return session.exec(statement).first()
        
    def create_user(self, master_id: int, username: str, email: str, full_name: str, **kwargs) -> User:
        """Cria um novo usuário vinculado a um master"""
        with session_scope() as session:
            # Verifica se o master existe
            master = session.get(Master, master_id)
            if not master:
                raise ValueError(f"Master com ID {master_id} não encontrado")
            
            # Verifica se já existe
            existing = self.get_user_by_username(username)
            if existing:
                raise ValueError(f"Usuário com username '{username}' já existe")
            
            existing_email = self.get_user_by_email(email)
            if existing_email:
                raise ValueError(f"Usuário com email '{email}' já existe")
            
            user = User(
                master_id=master_id,
                username=username,
                email=email,
                full_name=full_name,
                **kwargs
            )
            session.add(user)
            session.flush()
            session.refresh(user)
            return user
    
    def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        """Atualiza um usuário"""
        with session_scope() as session:
            user = session.get(User, user_id)
            if user:
                for key, value in kwargs.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                session.add(user)
                session.flush()
                session.refresh(user)
            return user
    
    def delete_user(self, user_id: int, soft_delete: bool = True) -> bool:
        """Deleta ou desativa um usuário"""
        with session_scope() as session:
            user = session.get(User, user_id)
            if user:
                if soft_delete:
                    user.is_active = False
                    session.add(user)
                else:
                    session.delete(user)
                session.flush()
                return True
            return False
    
    # ============ ASSISTANTS ============
    def get_all_assistants(self, active_only: bool = True) -> List[Assistant]:
        """Lista todas as assistentes"""
        with session_scope() as session:
            statement = select(Assistant)
            if active_only:
                statement = statement.where(Assistant.is_active == True)
            return session.exec(statement).all()
    
    def get_assistant_by_id(self, assistant_id: int) -> Optional[Assistant]:
        """Obtém uma assistente pelo ID"""
        with session_scope() as session:
            return session.get(Assistant, assistant_id)
    
    def get_assistant_by_user(self, user_id: int) -> Optional[Assistant]:
        """Obtém a assistente de um usuário"""
        with session_scope() as session:
            statement = select(Assistant).where(
                Assistant.user_id == user_id,
                Assistant.is_active == True
            )
            return session.exec(statement).first()
    
    def get_default_assistant(self) -> Optional[Assistant]:
        """Obtém a assistente padrão do sistema"""
        with session_scope() as session:
            statement = select(Assistant).where(
                Assistant.is_default == True,
                Assistant.is_active == True
            )
            return session.exec(statement).first()
    
    def create_assistant(self, master_id: int, user_id: int, name: str, **kwargs) -> Assistant:
        """Cria uma nova assistente para um usuário"""
        with session_scope() as session:
            # Verifica se o master existe
            master = session.get(Master, master_id)
            if not master:
                raise ValueError(f"Master com ID {master_id} não encontrado")
            
            # Verifica se o usuário existe
            user = session.get(User, user_id)
            if not user:
                raise ValueError(f"Usuário com ID {user_id} não encontrado")
            
            # Se for a primeira assistente do usuário, torna padrão
            existing = self.get_assistant_by_user(user_id)
            is_default = kwargs.get('is_default', existing is None)
            
            assistant = Assistant(
                master_id=master_id,
                user_id=user_id,
                name=name,
                is_default=is_default,
                **kwargs
            )
            session.add(assistant)
            session.flush()
            session.refresh(assistant)
            return assistant
    
    def update_assistant(self, assistant_id: int, **kwargs) -> Optional[Assistant]:
        """Atualiza configurações da assistente"""
        with session_scope() as session:
            assistant = session.get(Assistant, assistant_id)
            if assistant:
                for key, value in kwargs.items():
                    if hasattr(assistant, key):
                        setattr(assistant, key, value)
                session.add(assistant)
                session.flush()
                session.refresh(assistant)
            return assistant
    
    def set_default_assistant(self, assistant_id: int) -> Optional[Assistant]:
        """Define uma assistente como padrão"""
        with session_scope() as session:
            # Remove o padrão de todas as outras
            session.query(Assistant).update({Assistant.is_default: False})
            
            # Define a nova como padrão
            assistant = session.get(Assistant, assistant_id)
            if assistant:
                assistant.is_default = True
                session.add(assistant)
                session.flush()
                session.refresh(assistant)
            return assistant
    
    def delete_assistant(self, assistant_id: int, soft_delete: bool = True) -> bool:
        """Deleta ou desativa uma assistente"""
        with session_scope() as session:
            assistant = session.get(Assistant, assistant_id)
            if assistant:
                if soft_delete:
                    assistant.is_active = False
                    session.add(assistant)
                else:
                    session.delete(assistant)
                session.flush()
                return True
            return False