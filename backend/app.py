from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import date, datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from fastapi import Depends, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

DATABASE_URL = "sqlite:///./school.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Turma(Base):
    __tablename__ = "turmas"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)
    capacidade = Column(Integer)
    alunos = relationship("Aluno", back_populates="turma")

class Aluno(Base):
    __tablename__ = "alunos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    data_nascimento = Column(Date)
    email = Column(String, unique=True, nullable=True)
    status = Column(String, default="inativo")
    turma_id = Column(Integer, ForeignKey("turmas.id"), nullable=True)
    turma = relationship("Turma", back_populates="alunos")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Gestão Escolar API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AlunoIn(BaseModel):
    nome: str = Field(..., min_length=3, max_length=80)
    data_nascimento: date
    email: Optional[EmailStr] = None
    status: str = Field(...)
    turma_id: Optional[int] = None

    @validator("data_nascimento")
    def check_age(cls, v: date):
        min_date = date.today() - timedelta(days=365*5)
        if v > min_date:
            raise ValueError("Aluno deve ter ao menos 5 anos")
        return v

class TurmaIn(BaseModel):
    nome: str
    capacidade: int


# --- Autenticação simples (JWT)
SECRET_KEY = "dev-secret-key-change-me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def get_password_hash(password):
    return pwd_context.hash(password)

# usuário administrador hardcoded para demo
FAKE_USERS_DB = {
    "admin": {"username": "admin", "full_name": "Admin", "hashed_password": get_password_hash("adminpass"), "disabled": False}
}

def authenticate_user(username: str, password: str):
    user = FAKE_USERS_DB.get(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = FAKE_USERS_DB.get(username)
    if user is None:
        raise credentials_exception
    return user

def require_admin(user=Depends(get_current_user)):
    # placeholder — in real system checar permissões
    return user

# Middleware de tratamento global de erros
@app.middleware("http")
async def global_error_handler(request, call_next):
    try:
        return await call_next(request)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


class MatriculaIn(BaseModel):
    aluno_id: int
    turma_id: int

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/login", tags=["auth"], summary="Login de administrador")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Usuário ou senha inválidos")
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/alunos", tags=["alunos"], summary="Listar alunos com filtros")
def list_alunos(search: Optional[str] = None, turma_id: Optional[int] = None, status: Optional[str] = None, page: int = 1, per_page: int = 50):
    db = SessionLocal()
    q = db.query(Aluno)
    if search:
        q = q.filter(Aluno.nome.contains(search))
    if turma_id:
        q = q.filter(Aluno.turma_id == turma_id)
    if status:
        q = q.filter(Aluno.status == status)
    total = q.count()
    results = q.offset((page-1)*per_page).limit(per_page).all()
    # serializar manualmente para evitar problemas com tipos
    out = []
    for a in results:
        out.append({
            "id": a.id,
            "nome": a.nome,
            "data_nascimento": a.data_nascimento.isoformat() if a.data_nascimento else None,
            "email": a.email,
            "status": a.status,
            "turma_id": a.turma_id,
            "turma": a.turma.nome if a.turma else None,
        })
    return {"total": total, "page": page, "per_page": per_page, "results": out}

@app.post("/alunos")
def create_aluno(payload: AlunoIn):
    db = SessionLocal()
    # email duplicado?
    if payload.email:
        exists = db.query(Aluno).filter(Aluno.email == payload.email).first()
        if exists:
            raise HTTPException(status_code=400, detail="Email já cadastrado")
    # se houver turma_id, verificar capacidade
    if payload.turma_id:
        turma = db.query(Turma).get(payload.turma_id)
        if not turma:
            raise HTTPException(status_code=404, detail="Turma não encontrada")
        ocupacao = db.query(Aluno).filter(Aluno.turma_id == turma.id).count()
        if ocupacao >= turma.capacidade:
            raise HTTPException(status_code=400, detail="Turma cheia")
        payload.status = "ativo"

    aluno = Aluno(nome=payload.nome, data_nascimento=payload.data_nascimento, email=payload.email, status=payload.status, turma_id=payload.turma_id)
    db.add(aluno)
    db.commit()
    db.refresh(aluno)
    return {
        "id": aluno.id,
        "nome": aluno.nome,
        "data_nascimento": aluno.data_nascimento.isoformat() if aluno.data_nascimento else None,
        "email": aluno.email,
        "status": aluno.status,
        "turma_id": aluno.turma_id,
    }

@app.put("/alunos/{id}")
def update_aluno(id: int, payload: AlunoIn):
    db = SessionLocal()
    aluno = db.query(Aluno).get(id)
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    # verificar email duplicado
    if payload.email:
        exists = db.query(Aluno).filter(Aluno.email == payload.email, Aluno.id != id).first()
        if exists:
            raise HTTPException(status_code=400, detail="Email já cadastrado")
    aluno.nome = payload.nome
    aluno.data_nascimento = payload.data_nascimento
    aluno.email = payload.email
    aluno.status = payload.status
    aluno.turma_id = payload.turma_id
    db.commit()
    db.refresh(aluno)
    return {
        "id": aluno.id,
        "nome": aluno.nome,
        "data_nascimento": aluno.data_nascimento.isoformat() if aluno.data_nascimento else None,
        "email": aluno.email,
        "status": aluno.status,
        "turma_id": aluno.turma_id,
    }

@app.delete("/alunos/{id}")
def delete_aluno(id: int):
    db = SessionLocal()
    aluno = db.query(Aluno).get(id)
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    db.delete(aluno)
    db.commit()
    return {"detail": "Deletado"}

@app.get("/turmas")
def list_turmas():
    db = SessionLocal()
    return db.query(Turma).all()

@app.post("/turmas")
def create_turma(payload: TurmaIn, user=Depends(require_admin)):
    db = SessionLocal()
    # validações custom
    if payload.capacidade < 1:
        raise HTTPException(status_code=400, detail="Capacidade da turma deve ser ao menos 1")
    turma = Turma(nome=payload.nome, capacidade=payload.capacidade)
    db.add(turma)
    db.commit()
    db.refresh(turma)
    return turma


@app.put("/turmas/{id}", tags=["turmas"], summary="Atualizar turma")
def update_turma(id: int, payload: TurmaIn, user=Depends(require_admin)):
    db = SessionLocal()
    turma = db.query(Turma).get(id)
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    if payload.capacidade < 1:
        raise HTTPException(status_code=400, detail="Capacidade da turma deve ser ao menos 1")
    turma.nome = payload.nome
    turma.capacidade = payload.capacidade
    db.commit()
    db.refresh(turma)
    return turma


@app.delete("/turmas/{id}", tags=["turmas"], summary="Deletar turma")
def delete_turma(id: int, user=Depends(require_admin)):
    db = SessionLocal()
    turma = db.query(Turma).get(id)
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    ocupacao = db.query(Aluno).filter(Aluno.turma_id == turma.id).count()
    if ocupacao > 0:
        raise HTTPException(status_code=400, detail="Não é possível excluir turma com alunos matriculados")
    db.delete(turma)
    db.commit()
    return {"detail": "Turma deletada"}


@app.get("/export/alunos")
def export_alunos(format: str = "csv", search: Optional[str] = None, turma_id: Optional[int] = None, status: Optional[str] = None):
    import io, csv
    db = SessionLocal()
    q = db.query(Aluno)
    if search:
        q = q.filter(Aluno.nome.contains(search))
    if turma_id:
        q = q.filter(Aluno.turma_id == turma_id)
    if status:
        q = q.filter(Aluno.status == status)
    alunos = q.all()
    if format == "json":
        data = []
        for a in alunos:
            data.append({
                "id": a.id,
                "nome": a.nome,
                "data_nascimento": a.data_nascimento.isoformat() if a.data_nascimento else None,
                "email": a.email,
                "status": a.status,
                "turma_id": a.turma_id,
                "turma": a.turma.nome if a.turma else None,
            })
        return JSONResponse(content=data)

    # CSV
    def generate():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["id", "nome", "data_nascimento", "email", "status", "turma_id", "turma"])
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        for a in alunos:
            writer.writerow([a.id, a.nome, a.data_nascimento.isoformat() if a.data_nascimento else '', a.email or '', a.status, a.turma_id or '', a.turma.nome if a.turma else ''])
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    return StreamingResponse(generate(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=alunos.csv"})


@app.get("/export/matriculas")
def export_matriculas(format: str = "csv", turma_id: Optional[int] = None):
    import io, csv
    db = SessionLocal()
    q = db.query(Aluno).filter(Aluno.turma_id != None)
    if turma_id:
        q = q.filter(Aluno.turma_id == turma_id)
    alunos = q.all()
    if format == "json":
        data = []
        for a in alunos:
            data.append({
                "aluno_id": a.id,
                "nome": a.nome,
                "turma_id": a.turma_id,
                "turma": a.turma.nome if a.turma else None,
                "data_nascimento": a.data_nascimento.isoformat() if a.data_nascimento else None,
                "email": a.email,
            })
        return JSONResponse(content=data)

    def generate():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["aluno_id", "nome", "turma_id", "turma", "data_nascimento", "email"])
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        for a in alunos:
            writer.writerow([a.id, a.nome, a.turma_id or '', a.turma.nome if a.turma else '', a.data_nascimento.isoformat() if a.data_nascimento else '', a.email or ''])
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    return StreamingResponse(generate(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=matriculas.csv"})

@app.post("/matriculas")
def matricular(payload: MatriculaIn):
    db = SessionLocal()
    aluno = db.query(Aluno).get(payload.aluno_id)
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    turma = db.query(Turma).get(payload.turma_id)
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    ocupacao = db.query(Aluno).filter(Aluno.turma_id == turma.id).count()
    if ocupacao >= turma.capacidade:
        raise HTTPException(status_code=400, detail="Turma cheia")
    aluno.turma_id = turma.id
    aluno.status = "ativo"
    db.commit()
    db.refresh(aluno)
    return {"detail": "Matriculado", "aluno": aluno}
