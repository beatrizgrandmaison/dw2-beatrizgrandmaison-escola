from datetime import date, timedelta
from random import randint, choice
from app import SessionLocal, Turma, Aluno, Base, engine

Base.metadata.create_all(bind=engine)

db = SessionLocal()
# limpar
db.query(Aluno).delete()
db.query(Turma).delete()

turmas = []
for i in range(1,6):
    t = Turma(nome=f"Turma {i}", capacidade=randint(10,25))
    db.add(t)
    turmas.append(t)

db.commit()

names = [
    "Ana", "Bruno", "Carla", "Daniel", "Eduarda", "Fábio", "Gisele", "Henrique",
    "Isabela", "João", "Karla", "Luan", "Marta", "Nicolas", "Olivia", "Paulo",
    "Quésia", "Rafaela", "Sérgio", "Tânia"
]

for i, name in enumerate(names):
    dob = date.today() - timedelta(days=365*(6 + randint(0,12)))
    a = Aluno(nome=name, data_nascimento=dob, email=f"{name.lower()}@exemplo.com", status=choice(["ativo","inativo"]), turma_id=choice([t.id for t in turmas] + [None]))
    db.add(a)

db.commit()
print("Seed finalizado")
