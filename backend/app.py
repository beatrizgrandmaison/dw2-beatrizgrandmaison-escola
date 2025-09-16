from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import date, datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

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

class MatriculaIn(BaseModel):
    aluno_id: int
    turma_id: int

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/alunos")
def list_alunos(search: Optional[str] = None, turma_id: Optional[int] = None, status: Optional[str] = None):
    db = SessionLocal()
    q = db.query(Aluno)
    if search:
        q = q.filter(Aluno.nome.contains(search))
    if turma_id:
        q = q.filter(Aluno.turma_id == turma_id)
    if status:
        q = q.filter(Aluno.status == status)
    results = q.all()
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
    return out

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
def create_turma(payload: TurmaIn):
    db = SessionLocal()
    # validações custom
    if payload.capacidade < 1:
        raise HTTPException(status_code=400, detail="Capacidade da turma deve ser ao menos 1")
    turma = Turma(nome=payload.nome, capacidade=payload.capacidade)
    db.add(turma)
    db.commit()
    db.refresh(turma)
    return turma


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
