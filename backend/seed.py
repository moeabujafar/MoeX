from backend import db
from backend.main import _hash_secret

def seed_person(name, email, tags, secret_word, handle=None, persona=None):
    salt, h = _hash_secret(secret_word)
    person_id = db.execute(
        """INSERT INTO people(name,email,handle,tags,persona,secret_salt,secret_hash,is_enabled)
           VALUES(?,?,?,?,?,?,?,1)""",
        (name, email, handle, tags, persona, salt, h),
    )
    print(f"✅ Seeded {name} (id={person_id})")
    return person_id

if __name__ == "__main__":
    # Example: seed Fatima with persona
    seed_person(
        name="Fatima Alzaabi",
        email="fatima.alzaabi@mbzuai.ac.ae",
        tags="Finance, AR, Student Billing",
        secret_word="orchid",   # her secret keyword
        handle="fatima",        # lowercase is easier to reference
        persona="Keep answers short, use bullet points, highlight AR deadlines."
    )
