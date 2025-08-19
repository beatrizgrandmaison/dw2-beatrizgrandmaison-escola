from fastapi import FastAPI, HTTPException
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
    email = Column(String, nullable=True)
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
    return results

@app.post("/alunos")
def create_aluno(payload: AlunoIn):
    db = SessionLocal()
    aluno = Aluno(nome=payload.nome, data_nascimento=payload.data_nascimento, email=payload.email, status=payload.status, turma_id=payload.turma_id)
    db.add(aluno)
    db.commit()
    db.refresh(aluno)
    return aluno

@app.put("/alunos/{id}")
def update_aluno(id: int, payload: AlunoIn):
    db = SessionLocal()
    aluno = db.query(Aluno).get(id)
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    aluno.nome = payload.nome
    aluno.data_nascimento = payload.data_nascimento
    aluno.email = payload.email
    aluno.status = payload.status
    aluno.turma_id = payload.turma_id
    db.commit()
    db.refresh(aluno)
    return aluno

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
    turma = Turma(nome=payload.nome, capacidade=payload.capacidade)
    db.add(turma)
    db.commit()
    db.refresh(turma)
    return turma

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
