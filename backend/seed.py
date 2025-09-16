from datetime import date, timedelta
from random import randint, choice, sample
from app import SessionLocal, Turma, Aluno, Base, engine

Base.metadata.create_all(bind=engine)

db = SessionLocal()
# limpar existente
db.query(Aluno).delete()
db.query(Turma).delete()
db.commit()

# criar 5 turmas
turmas = []
for i in range(1,6):
    t = Turma(nome=f"Turma {i}", capacidade=randint(8,20))
    db.add(t)
    turmas.append(t)
db.commit()

# criar 20 alunos com emails únicos
first_names = [
    "Ana", "Bruno", "Carla", "Daniel", "Eduarda", "Fábio", "Gisele", "Henrique",
    "Isabela", "João", "Karla", "Luan", "Marta", "Nicolas", "Olivia", "Paulo",
    "Quésia", "Rafaela", "Sérgio", "Tânia",
]

for i, name in enumerate(first_names, start=1):
    years = 6 + randint(0,12)
    dob = date.today() - timedelta(days=365*years)
    email = f"{name.lower()}.{i}@example.com"
    turma_choice = choice(turmas + [None, None])
    turma_id = turma_choice.id if turma_choice else None
    status = choice(["ativo", "inativo"])
    a = Aluno(nome=name, data_nascimento=dob, email=email, status=status, turma_id=turma_id)
    db.add(a)

db.commit()
print("Seed finalizado: 5 turmas e 20 alunos criados")
