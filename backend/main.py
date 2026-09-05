import base64
import binascii
import json
import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_current_user,
    register_user,
    verify_token,
)
from .config import (
    APP_VERSION,
    CHUNK_SIZE,
    CORS_ALLOW_HEADERS,
    CORS_ALLOW_METHODS,
    CORS_ORIGINS,
    GEMINI_API_KEY,
    MAX_FILE_SIZE,
)
from .database import Analysis, ChatMessage, User, UserCategory, engine, get_db, init_db
from .database import File as FileModel
from .parsers import parse_csv, parse_excel, parse_ofx, parse_pdf
from .services.analysis import (
    analyze_transactions,
    categorize_transaction,
    decode_user_categories,
    format_analysis_for_ai,
)
from .services.export import ExportService
from .services.gemini import GeminiAPIError, GeminiService, aclose_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("backend").setLevel(logging.INFO)
    logger.info("Application logging configured for upload diagnostics")
    yield
    await aclose_client()


app = FastAPI(
    title="InvestIA API",
    version=APP_VERSION,
    lifespan=lifespan,
    description="""
## InvestIA - Análise Financeira com IA

API para análise de extratos bancários com inteligência artificial.

### Funcionalidades
- **Upload multi-formato**: OFX, QFX, CSV, XLSX, PDF (máx 10MB)
- **Categorização automática**: 12 categorias com 150+ keywords
- **Análise financeira**: Receitas, despesas, saldo, recorrentes, alertas
- **IA Gemini 3.5 Flash**: Insights personalizados e chat
- **Export**: HTML, CSV, JSON
- **Auth**: JWT (24h expiração)

### Autenticação
Todas as rotas (exceto `/api/health`, `/api/auth/login` e `/api/auth/register`) requerem header:
```
Authorization: Bearer <token>
```

Registre-se em `POST /api/auth/register` ou faça login em `POST /api/auth/login`.
""",
    contact={
        "name": "InvestIA",
        "url": "https://github.com/seu-usuario/InvestIA",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)

# Headers de segurança em todas as respostas (fixo, leve, stateless).
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

MAX_CHAT_TRANSACTIONS = 100  # limit transactions sent to Gemini in chat context

# Rate limiting storage
rate_limit_store: dict[str, list[tuple[str, float]]] = {}
RATE_LIMIT_MAX_LOGIN = 15
RATE_LIMIT_MAX_REGISTER = 20
RATE_LIMIT_WINDOW = 60  # seconds


def check_rate_limit(ip: str, endpoint: str = "default") -> bool:
    now = time.time()
    key = f"{ip}:{endpoint}"
    if key not in rate_limit_store:
        rate_limit_store[key] = []
    rate_limit_store[key] = [t for t in rate_limit_store[key] if now - t < RATE_LIMIT_WINDOW]
    if not rate_limit_store[key]:
        del rate_limit_store[key]
        rate_limit_store[key] = []
    max_requests = RATE_LIMIT_MAX_LOGIN if endpoint == "login" else RATE_LIMIT_MAX_REGISTER
    if len(rate_limit_store[key]) >= max_requests:
        return False
    rate_limit_store[key].append(now)
    return True


init_db()


def get_gemini() -> GeminiService:
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY não configurada")
    return GeminiService(GEMINI_API_KEY)


# --- Auth ---

class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AvatarUpdateRequest(BaseModel):
    avatar_url: str


AVATAR_MAX_BYTES = 2 * 1024 * 1024
AVATAR_PREFIXES = {
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/jpeg": b"\xff\xd8\xff",
}


def _decode_avatar(avatar_url: str) -> str:
    """Validate an avatar data URL before storing it with the user account."""
    try:
        header, encoded_image = avatar_url.split(",", 1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Imagem de perfil inválida") from None

    allowed_headers = {f"data:{mime};base64": mime for mime in (*AVATAR_PREFIXES, "image/webp")}
    mime_type = allowed_headers.get(header.lower())
    if not mime_type:
        raise HTTPException(status_code=400, detail="Use uma imagem PNG, JPEG ou WebP")

    try:
        image_bytes = base64.b64decode(encoded_image, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="Imagem de perfil inválida") from None

    if not image_bytes or len(image_bytes) > AVATAR_MAX_BYTES:
        raise HTTPException(status_code=400, detail="A imagem deve ter no máximo 2 MB")

    is_valid_image = (
        image_bytes.startswith(AVATAR_PREFIXES.get(mime_type, b""))
        if mime_type != "image/webp"
        else image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP"
    )
    if not is_valid_image:
        raise HTTPException(status_code=400, detail="O conteúdo não corresponde ao tipo da imagem")

    return f"data:{mime_type};base64,{encoded_image}"


@app.post("/api/auth/register", summary="Criar conta",
          description="Registra novo usuário com email, nome e senha. Retorna JWT token.")
def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip, "register"):
        raise HTTPException(status_code=429, detail="Muitas requisições. Tente novamente em 1 minuto.")
    user = register_user(db, req.email, req.name, req.password)
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"sub": str(user.id), "email": user.email})
    return {
        "token": access_token,
        "refresh_token": refresh_token,
        "user": {"id": user.id, "email": user.email, "name": user.name, "avatar_url": user.avatar_url},
    }


@app.post("/api/auth/login", summary="Login", description="Autentica usuário com email e senha. Retorna JWT token.")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip, "login"):
        raise HTTPException(status_code=429, detail="Muitas requisições. Tente novamente em 1 minuto.")
    user = authenticate_user(db, req.email, req.password)
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"sub": str(user.id), "email": user.email})
    return {
        "token": access_token,
        "refresh_token": refresh_token,
        "user": {"id": user.id, "email": user.email, "name": user.name, "avatar_url": user.avatar_url},
    }


@app.get("/api/auth/me", summary="Usuário atual", description="Retorna dados do usuário autenticado.")
def get_me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "name": user.name, "avatar_url": user.avatar_url}


@app.post("/api/auth/avatar", summary="Atualizar foto de perfil")
def update_avatar(req: AvatarUpdateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.avatar_url = _decode_avatar(req.avatar_url)
    db.commit()
    db.refresh(user)
    return {"user": {"id": user.id, "email": user.email, "name": user.name, "avatar_url": user.avatar_url}}


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@app.post("/api/auth/refresh", summary="Renovar access token",
          description="Recebe um refresh token e retorna um novo access token.")
def refresh_token(req: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = verify_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token inválido: não é um refresh token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")
    try:
        user_pk = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Token inválido") from None
    user = db.query(User).filter(User.id == user_pk).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"sub": str(user.id), "email": user.email})
    return {
        "token": access_token,
        "refresh_token": refresh_token,
    }


# --- Files ---

@app.post("/api/upload", summary="Upload de extrato",
          description="Envia arquivo OFX, QFX, CSV, XLSX, XLS ou PDF (máx 10MB). "
                      "Retorna dados parseados e ID do arquivo.")
async def upload_file(
    file: UploadFile = File(..., description="Arquivo de extrato bancário"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename or "." not in file.filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido")

    ext = file.filename.rsplit(".", 1)[-1].lower()

    parsers = {
        "ofx": parse_ofx,
        "qfx": parse_ofx,
        "csv": parse_csv,
        "xlsx": parse_excel,
        "xls": parse_excel,
        "pdf": parse_pdf,
    }

    parser = parsers.get(ext)
    if not parser:
        raise HTTPException(status_code=400, detail=f"Tipo de arquivo '{ext}' não suportado")

    # Stream the upload in chunks, rejecting oversized files without loading
    # the whole body into memory.
    content = b""
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        content += chunk
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Arquivo muito grande. Tamanho máximo: {MAX_FILE_SIZE // (1024*1024)}MB"
            )

    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    if ext in ("ofx", "qfx"):
        parsed = parser(content)
    elif ext == "csv":
        parsed = parser(content, file.filename)
    elif ext in ("xlsx", "xls"):
        parsed = parser(content, file.filename)
    else:
        parsed = parser(content)

    if ext == "pdf":
        diagnostics = parsed.get("_diagnostics", {})
        logger.info(
            "PDF upload parsed: size_bytes=%d pages=%s tables=%s methods=%s transactions=%s",
            len(content),
            parsed.get("pages"),
            diagnostics.get("tables_found"),
            diagnostics.get("extraction_methods"),
            parsed.get("total_transactions"),
        )

    db_file = FileModel(
        user_id=user.id,
        filename=file.filename,
        file_type=ext,
        file_size=len(content),
        parsed_data=json.dumps(parsed, ensure_ascii=False, default=str),
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    return {
        "id": db_file.id,
        "filename": db_file.filename,
        "file_type": db_file.file_type,
        "file_size": db_file.file_size,
        "parsed": parsed,
    }


@app.get("/api/files", summary="Listar arquivos",
         description="Retorna os arquivos do usuário mais recentes primeiro. "
                     "Sem parâmetros de paginação retorna a lista completa "
                     "(contrato original); informe page/page_size para paginar "
                     "e receber {items, total, page, page_size}.")
def list_files(
    page: int | None = None,
    page_size: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(FileModel).filter(FileModel.user_id == user.id)

    if page is None and page_size is None:
        files = query.order_by(FileModel.created_at.desc()).all()
        return [
            {
                "id": f.id,
                "filename": f.filename,
                "file_type": f.file_type,
                "file_size": f.file_size,
                "created_at": f.created_at.isoformat(),
            }
            for f in files
        ]

    page = max(1, page or 1)
    page_size = max(1, min(200, page_size or 50))
    offset = (page - 1) * page_size
    files = (
        query.order_by(FileModel.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    total = query.count()
    return {
        "items": [
            {
                "id": f.id,
                "filename": f.filename,
                "file_type": f.file_type,
                "file_size": f.file_size,
                "created_at": f.created_at.isoformat(),
            }
            for f in files
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.delete("/api/files/{file_id}", summary="Remover arquivo", description="Exclui arquivo do usuário pelo ID.")
def delete_file(file_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    file = db.query(FileModel).filter(FileModel.id == file_id, FileModel.user_id == user.id).first()
    if not file:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    db.delete(file)
    db.commit()
    return {"ok": True}


# --- Analysis ---

class AnalysisRequest(BaseModel):
    file_id: int | None = None
    analysis_type: str = "full"
    user_context: str | None = None


@app.post("/api/analysis", summary="Análise financeira",
          description="Executa análise completa (local + IA) nos dados do arquivo. "
                      "Requer file_id ou usa o mais recente.")
async def run_analysis(
    req: AnalysisRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    gemini: GeminiService = Depends(get_gemini),
):
    parsed_data = None
    used_file_id = req.file_id

    if req.file_id:
        file = (
            db.query(FileModel)
            .filter(FileModel.id == req.file_id, FileModel.user_id == user.id)
            .first()
        )
        if not file:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado")
        parsed_data = json.loads(file.parsed_data)
    else:
        files = (
            db.query(FileModel)
            .filter(FileModel.user_id == user.id)
            .order_by(FileModel.created_at.desc())
            .limit(1)
            .first()
        )
        if files:
            parsed_data = json.loads(files.parsed_data)
            used_file_id = files.id

    if not parsed_data:
        raise HTTPException(status_code=400, detail="Nenhum arquivo encontrado para análise")

    # Run local analysis
    transactions = parsed_data.get("transactions", [])
    user_cats = db.query(UserCategory).filter(UserCategory.user_id == user.id).all()
    user_categories_list = [{"name": c.name, "keywords": c.keywords} for c in user_cats]
    local_analysis = analyze_transactions(transactions, user_categories_list) if transactions else {}

    # Enrich with AI (limit transactions for Gemini context)
    limited_txns = transactions[:500]
    limited_parsed = {**parsed_data, "transactions": limited_txns}
    if local_analysis:
        context = format_analysis_for_ai(local_analysis, limited_parsed)
    else:
        context = json.dumps(limited_parsed, indent=2)
    try:
        ai_prompt = f"Analise estes dados financeiros:\n\n{context}\n\n{req.user_context or ''}"
        ai_response = await gemini.chat([{"role": "user", "content": ai_prompt}])
    except GeminiAPIError:
        raise HTTPException(status_code=502, detail="Serviço de IA indisponível no momento") from None

    result = {
        "local_analysis": local_analysis,
        "ai_analysis": ai_response,
        "file_info": {"filename": parsed_data.get("type", "unknown"), "summary": parsed_data.get("summary", "")},
    }

    db_analysis = Analysis(
        user_id=user.id,
        file_id=used_file_id,
        analysis_type=req.analysis_type,
        result=json.dumps(result, ensure_ascii=False, default=str),
    )
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)

    return {"id": db_analysis.id, "result": result}


@app.get("/api/analysis/history", summary="Histórico de análises",
         description="Lista análises do usuário. Sem parâmetros de paginação "
                     "retorna a lista completa (contrato original); informe "
                     "page/page_size para paginar.")
def analysis_history(
    page: int | None = None,
    page_size: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Analysis).filter(Analysis.user_id == user.id)

    if page is None and page_size is None:
        analyses = query.order_by(Analysis.created_at.desc()).all()
        return [
            {"id": a.id, "type": a.analysis_type, "created_at": a.created_at.isoformat()}
            for a in analyses
        ]

    page = max(1, page or 1)
    page_size = max(1, min(200, page_size or 50))
    offset = (page - 1) * page_size
    analyses = (
        query.order_by(Analysis.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    total = query.count()
    return {
        "items": [
            {"id": a.id, "type": a.analysis_type, "created_at": a.created_at.isoformat()}
            for a in analyses
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.delete("/api/analysis/{analysis_id}", summary="Excluir análise", description="Exclui uma análise do usuário.")
def delete_analysis(analysis_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == user.id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Análise não encontrada")
    db.delete(analysis)
    db.commit()
    return {"ok": True}


# --- Investment ---

class InvestmentRequest(BaseModel):
    profile: str = "Moderado"
    amount: float = 1000
    categories: list[str] = ["fii", "acoes", "tesouro", "cdb"]


@app.post("/api/investment", summary="Recomendação de investimento",
          description="Gera recomendação personalizada baseada em perfil, valor e categorias preferidas.")
async def investment_recommendation(
    req: InvestmentRequest,
    user: User = Depends(get_current_user),
    gemini: GeminiService = Depends(get_gemini),
):
    try:
        result = await gemini.generate_investment_recommendation(req.profile, req.amount, req.categories)
    except GeminiAPIError:
        raise HTTPException(status_code=502, detail="Serviço de IA indisponível no momento") from None
    return {"recommendation": result}


# --- Chat ---

class ChatRequest(BaseModel):
    message: str
    file_id: int | None = None


@app.post("/api/chat", summary="Chat com IA",
          description="Conversa com assistente financeiro. Opcionalmente inclui "
                      "contexto de arquivo via file_id.")
async def chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    gemini: GeminiService = Depends(get_gemini),
):
    # Save user message
    user_msg = ChatMessage(user_id=user.id, role="user", content=req.message)
    db.add(user_msg)
    db.commit()

    # Get chat history
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(20)
        .all()
    )
    history.reverse()

    messages = [{"role": m.role, "content": m.content} for m in history]

    # Add file context if provided
    if req.file_id:
        file = (
            db.query(FileModel)
            .filter(FileModel.id == req.file_id, FileModel.user_id == user.id)
            .first()
        )
        if file:
            parsed = json.loads(file.parsed_data)
            transactions = parsed.get("transactions", [])
            if transactions:
                limited_txns = transactions[:MAX_CHAT_TRANSACTIONS]
                user_cats = db.query(UserCategory).filter(UserCategory.user_id == user.id).all()
                user_categories_list = [{"name": c.name, "keywords": c.keywords} for c in user_cats]
                local = analyze_transactions(limited_txns, user_categories_list)
                context = format_analysis_for_ai(local, parsed)
                chat_context = f"Contexto do arquivo {file.filename}:\n{context}"
                messages.insert(0, {"role": "user", "content": chat_context})

    try:
        response = await gemini.chat(messages)
    except GeminiAPIError:
        raise HTTPException(status_code=502, detail="Serviço de IA indisponível no momento") from None

    # Save assistant message
    assistant_msg = ChatMessage(user_id=user.id, role="assistant", content=response)
    db.add(assistant_msg)
    db.commit()

    return {"response": response}


@app.get("/api/chat/history", summary="Histórico do chat",
         description="Retorna mensagens do usuário (mais antigas primeiro). "
                     "Sem parâmetros de paginação retorna a lista completa "
                     "(contrato original); informe page/page_size para paginar.")
def chat_history(
    page: int | None = None,
    page_size: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ChatMessage).filter(ChatMessage.user_id == user.id)

    if page is None and page_size is None:
        messages = query.order_by(ChatMessage.created_at.asc()).all()
        return [
            {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in messages
        ]

    page = max(1, page or 1)
    page_size = max(1, min(200, page_size or 50))
    offset = (page - 1) * page_size
    total = query.count()
    messages = (
        query.order_by(ChatMessage.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    messages.reverse()
    return {
        "items": [
            {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in messages
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# --- Export ---

class ExportRequest(BaseModel):
    analysis_id: int
    format: str = "html"


@app.post("/api/reports/export", summary="Exportar relatório",
          description="Gera relatório em HTML, CSV, JSON ou PDF da análise especificada.")
async def export_report(
    req: ExportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if req.format not in ("html", "csv", "json", "pdf"):
        raise HTTPException(status_code=400, detail=f"Formato '{req.format}' não suportado. Use: html, csv, json, pdf")
    analysis = db.query(Analysis).filter(Analysis.id == req.analysis_id, Analysis.user_id == user.id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Análise não encontrada")

    result = json.loads(analysis.result)
    local = result.get("local_analysis", {})
    ai_text = result.get("ai_analysis", "")
    file_info = result.get("file_info", {})

    parsed_data = {}
    if analysis.file_id:
        file = db.query(FileModel).filter(FileModel.id == analysis.file_id, FileModel.user_id == user.id).first()
        if file:
            parsed_data = json.loads(file.parsed_data)

    export_data = {**local}
    if not export_data.get("total_income") and parsed_data:
        export_data["total_income"] = parsed_data.get("total_income", 0)
        export_data["total_expenses"] = parsed_data.get("total_expenses", 0)
        export_data["balance"] = parsed_data.get(
            "balance",
            parsed_data.get("total_income", 0) - parsed_data.get("total_expenses", 0),
        )
    if not export_data.get("categories") and parsed_data.get("transactions"):
        user_cats = db.query(UserCategory).filter(UserCategory.user_id == user.id).all()
        user_categories_list = [{"name": c.name, "keywords": c.keywords} for c in user_cats]
        export_data = analyze_transactions(parsed_data["transactions"], user_categories_list)

    if req.format == "html":
        content = ExportService.generate_html_report(export_data, ai_text, file_info)
        media_type = "text/html"
        ext = "html"
    elif req.format == "csv":
        content = ExportService.generate_csv_data(export_data, ai_text)
        media_type = "text/csv"
        ext = "csv"
    elif req.format == "pdf":
        content = ExportService.generate_pdf_report(export_data, ai_text, file_info)
        media_type = "application/pdf"
        ext = "pdf"
    else:
        content = ExportService.generate_json_report(result)
        media_type = "application/json"
        ext = "json"

    from fastapi.responses import Response
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename=investia_report.{ext}"},
    )


# --- Dashboard ---

@app.get("/api/dashboard/summary", summary="Resumo do dashboard",
         description="Retorna contadores e última análise para o dashboard.")
def dashboard_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    files_count = db.query(FileModel).filter(FileModel.user_id == user.id).count()
    analyses_count = db.query(Analysis).filter(Analysis.user_id == user.id).count()
    messages_count = db.query(ChatMessage).filter(ChatMessage.user_id == user.id).count()

    last_analysis = (
        db.query(Analysis)
        .filter(Analysis.user_id == user.id)
        .order_by(Analysis.created_at.desc())
        .first()
    )
    last_result = None
    if last_analysis:
        last_result = json.loads(last_analysis.result).get("local_analysis", {})

    return {
        "files_count": files_count,
        "analyses_count": analyses_count,
        "messages_count": messages_count,
        "last_analysis": last_result,
    }


# --- Custom Categories ---

class CategoryRequest(BaseModel):
    name: str
    keywords: list[str]


@app.get("/api/categories", summary="Listar categorias personalizadas",
         description="Retorna todas as categorias personalizadas do usuário.")
def list_categories(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cats = db.query(UserCategory).filter(UserCategory.user_id == user.id).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "keywords": json.loads(c.keywords) if c.keywords else [],
            "created_at": c.created_at.isoformat(),
        }
        for c in cats
    ]


@app.post("/api/categories", summary="Criar categoria personalizada",
          description="Cria uma nova categoria com nome e palavras-chave para categorização.")
def create_category(req: CategoryRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cat = UserCategory(user_id=user.id, name=req.name, keywords=json.dumps(req.keywords, ensure_ascii=False))
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"id": cat.id, "name": cat.name, "keywords": req.keywords}


@app.delete("/api/categories/{category_id}", summary="Excluir categoria personalizada",
            description="Exclui uma categoria personalizada do usuário.")
def delete_category(category_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cat = db.query(UserCategory).filter(UserCategory.id == category_id, UserCategory.user_id == user.id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    db.delete(cat)
    db.commit()
    return {"ok": True}


class LearnRequest(BaseModel):
    assignments: list[dict]


@app.post("/api/categories/learn", summary="Aprender com atribuições de categorias")
def learn_categories(req: LearnRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for assignment in req.assignments:
        desc = assignment.get("description", "").strip()
        cat_name = assignment.get("category", "").strip()
        if not desc or not cat_name:
            continue

        existing = db.query(UserCategory).filter(
            UserCategory.user_id == user.id,
            UserCategory.name == cat_name,
        ).first()

        if existing:
            keywords = json.loads(existing.keywords) if existing.keywords else []
            words = [w.strip().lower() for w in desc.split() if len(w.strip()) > 3]
            for w in words:
                if w not in keywords:
                    keywords.append(w)
            existing.keywords = json.dumps(keywords, ensure_ascii=False)
        else:
            words = [w.strip().lower() for w in desc.split() if len(w.strip()) > 3]
            if words:
                cat = UserCategory(
                    user_id=user.id,
                    name=cat_name,
                    keywords=json.dumps(words, ensure_ascii=False),
                )
                db.add(cat)

    db.commit()
    return {"ok": True}


@app.get("/api/transactions/{file_id}", summary="Listar transações com categorias")
def get_transactions(file_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    file = db.query(FileModel).filter(FileModel.id == file_id, FileModel.user_id == user.id).first()
    if not file:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    parsed_data = json.loads(file.parsed_data)
    transactions = parsed_data.get("transactions", [])

    user_cats = db.query(UserCategory).filter(UserCategory.user_id == user.id).all()
    user_categories_list = [{"name": c.name, "keywords": c.keywords} for c in user_cats]
    decoded_cats = decode_user_categories(user_categories_list)

    result = []
    for txn in transactions:
        cat = categorize_transaction(txn.get("description", ""), decoded_cats or None)
        result.append({
            "date": txn.get("date", ""),
            "description": txn.get("description", ""),
            "amount": txn.get("amount", 0),
            "category": cat,
        })

    return result


@app.get("/api/health", summary="Health check", description="Verifica status da API, banco de dados e Gemini.")
def health(db: Session = Depends(get_db)):
    checks = {
        "api": "ok",
        "database": "ok",
        "gemini": "configured" if GEMINI_API_KEY else "not_configured",
    }

    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as e:
        checks["database"] = f"error: {str(e)}"

    return {
        "status": "ok" if all(v == "ok" or v == "configured" for v in checks.values()) else "degraded",
        "version": APP_VERSION,
        "checks": checks,
    }


@app.get("/api/_diagnostic", summary="Database diagnostic (temp)")
def diagnostic(db: Session = Depends(get_db)):
    users_count = db.query(User).count()
    files_count = db.query(FileModel).count()
    messages_count = db.query(ChatMessage).count()

    columns = [c["name"] for c in sa_inspect(engine).get_columns("users")]
    has_password_hash = "password_hash" in columns

    alembic_version = None
    try:
        row = db.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        if row:
            alembic_version = row[0]
    except SQLAlchemyError:
        pass

    return {
        "users_count": users_count,
        "files_count": files_count,
        "chat_messages_count": messages_count,
        "has_password_hash_column": has_password_hash,
        "alembic_version": alembic_version,
    }
