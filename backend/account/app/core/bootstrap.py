from sqlalchemy.orm import Session
from argon2 import PasswordHasher
from app.db.models import User
ph = PasswordHasher()

def ensure_admin_user(db: Session, *, email: str, password: str, display_name: str = "Admin"):
    """
    Creates an admin account on startup
    """
    email = email.lower().strip()
    row = db.query(User).filter(User.email == email).first()
    if row:
        if row.role != "ADMIN":
            row.role = "ADMIN"
            db.add(row); db.commit()
        return
    admin = User(email=email, password_hash=ph.hash(password), display_name=display_name, role="ADMIN")
    db.add(admin); db.commit()
