import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Request, HTTPException, Depends
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

# Importamos as configurações do banco que acabamos de criar
from database import get_db, FileMetadata, AuditLog

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 25 * 1024 * 1024))
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "csv", "xlsx", "txt"}

Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Usuário logado simulado (futuramente virá do sistema de Login)
USUARIO_LOGADO = "Keila (Diretoria)"

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def secure_filename(filename: str) -> str:
    return os.path.basename(filename)

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Arquivo inválido ou não selecionado.")

    # Adicionamos um UUID para evitar que arquivos com mesmo nome se sobrescrevam
    original_name = secure_filename(file.filename)
    safe_filename = f"{uuid.uuid4().hex}_{original_name}"
    file_path = Path(UPLOAD_DIR) / safe_filename

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo excede o limite de 25MB.")

    # Salva fisicamente
    with open(file_path, "wb") as f:
        f.write(content)

    # 1. Salva metadados no MySQL
    db_file = FileMetadata(
        filename=safe_filename,
        original_name=original_name,
        size_bytes=len(content),
        status="ATIVO",
        uploaded_by=USUARIO_LOGADO
    )
    db.add(db_file)

    # 2. Registra Auditoria de Upload
    log = AuditLog(filename=original_name, action="UPLOAD", performed_by=USUARIO_LOGADO)
    db.add(log)
    
    db.commit()

    return RedirectResponse(url="/files", status_code=303)

@app.get("/files")
async def list_files(request: Request, db: Session = Depends(get_db)):
    # Busca no banco apenas arquivos ATIVOS
    files = db.query(FileMetadata).filter(FileMetadata.status == "ATIVO").order_by(FileMetadata.uploaded_at.desc()).all()
    return templates.TemplateResponse("files.html", {"request": request, "files": files})

@app.get("/files/{filename}")
async def download_file(filename: str, db: Session = Depends(get_db)):
    file_path = Path(UPLOAD_DIR) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    
    # Registra Auditoria de Download
    log = AuditLog(filename=filename, action="DOWNLOAD", performed_by=USUARIO_LOGADO)
    db.add(log)
    db.commit()

    return FileResponse(path=str(file_path), filename=filename)

@app.post("/delete/{file_id}")
async def delete_file(file_id: int, request: Request, db: Session = Depends(get_db)):
    # Busca o arquivo no banco
    db_file = db.query(FileMetadata).filter(FileMetadata.id == file_id).first()
    if not db_file or db_file.status == "EXCLUIDO":
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    # 1. Exclusão Lógica no Banco (Muda o status)
    db_file.status = "EXCLUIDO"

    # 2. Registra Auditoria de Exclusão
    log = AuditLog(filename=db_file.original_name, action="DELETE", performed_by=USUARIO_LOGADO)
    db.add(log)
    db.commit()

    # 3. Exclusão Física (Apaga do HD para liberar espaço)
    file_path = Path(UPLOAD_DIR) / db_file.filename
    if file_path.exists():
        os.remove(file_path)

    return RedirectResponse(url="/files", status_code=303)