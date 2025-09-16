from datetime import date, timedelta
from random import randint, choice
from faker import Faker
from app import SessionLocal, Turma, Aluno, Base, engine
from sqlalchemy import text


def main(num_turmas: int = 5, num_alunos: int = 20, use_faker: bool = True):
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # limpar existente
        db.query(Aluno).delete()
        db.query(Turma).delete()
        db.commit()

        # resetar autoincrement do SQLite para começar IDs em 1
        with engine.begin() as conn:
            # sqlite keeps counters in sqlite_sequence
            conn.exec_driver_sql("DELETE FROM sqlite_sequence WHERE name='alunos'")
            conn.exec_driver_sql("DELETE FROM sqlite_sequence WHERE name='turmas'")

        # criar turmas
        turmas = []
        for i in range(1, num_turmas + 1):
            t = Turma(nome=f"Turma {i}", capacidade=randint(8, 20))
            db.add(t)
            turmas.append(t)
        db.commit()

        fake = Faker('pt_BR') if use_faker else None

        created_emails = set()
        for i in range(1, num_alunos + 1):
            if use_faker and fake:
                first = fake.first_name()
                last = fake.last_name()
                nome = f"{first} {last}"
                # garante faixa etária >=6
                dob = fake.date_of_birth(minimum_age=6, maximum_age=18)
                base_email = f"{first.lower()}.{last.lower()}"
            else:
                nome = f"Aluno {i}"
                years = 6 + randint(0, 12)
                dob = date.today() - timedelta(days=365 * years)
                base_email = f"aluno{i}"

            # garantir email único
            email = f"{base_email}@example.com"
            suffix = 1
            while db.query(Aluno).filter(Aluno.email == email).first() or email in created_emails:
                email = f"{base_email}{suffix}@example.com"
                suffix += 1
            created_emails.add(email)

            turma_choice = choice(turmas + [None, None])
            turma_id = turma_choice.id if turma_choice else None
            status = choice(["ativo", "inativo"]) if randint(0, 1) else "inativo"

            a = Aluno(nome=nome, data_nascimento=dob, email=email, status=status, turma_id=turma_id)
            db.add(a)

        db.commit()
        print(f"Seed finalizado: {num_turmas} turmas e {num_alunos} alunos criados")
    finally:
        db.close()


if __name__ == '__main__':
    # executa com Faker por padrão
    main()
