from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# Substitua pelas suas credenciais do MySQL 8
# Formato: mysql+pymysql://USUARIO:SENHA@HOST:PORTA/NOME_DO_BANCO
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:1234@localhost:3306/administracao"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Tabela de Metadados dos Arquivos
class FileMetadata(Base):
    __tablename__ = "files_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, index=True)
    original_name = Column(String(255))
    size_bytes = Column(Integer)
    status = Column(String(50), default="ATIVO") # ATIVO ou EXCLUIDO
    uploaded_by = Column(String(100))
    uploaded_at = Column(DateTime, default=datetime.now)

# Tabela de Auditoria (Histórico)
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))
    action = Column(String(50)) # UPLOAD, DOWNLOAD ou DELETE
    performed_by = Column(String(100))
    performed_at = Column(DateTime, default=datetime.now)

# Cria as tabelas automaticamente no MySQL se não existirem
Base.metadata.create_all(bind=engine)

# Dependência para pegar a sessão do banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()