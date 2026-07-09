from fastapi import APIRouter, Depends, status, HTTPException
from typing import Annotated
from sqlalchemy.orm import Session
from database import SessionLocal
from pydantic import BaseModel
from models import Users
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import timedelta, datetime, timezone

router = APIRouter(prefix="/auth", tags=["auth"])

SECRET_KEY = 'agh3paefaw3p98r9483tg794gh9q348p8t-f7er89t32uqtpg8h3028yfh2q3'
ALGORITHM = 'HS256'

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

class CreateUserRequest(BaseModel):
    username: str
    email: str
    firstname: str
    lastname: str
    password: str
    role: str

def authencate_user(username: str, password: str, db):
    user = db.query(Users).filter(Users.username == username).first()
    if not user:
        return False
    if not bcrypt_context.verify(password, user.hashedpassword):
        return False
    return user

def create_access_token(username: str, user_id: int, expite_delta: timedelta):
    encode = {'sub': username, 'id': user_id}
    expires = datetime.now(timezone.utc) + expite_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        user_id: int = payload.get('id')
        print(payload)
        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Could not validata user.')
        return {'username': username, 'id': user_id}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail='Could not validata user.')


@router.get('/', status_code=status.HTTP_200_OK)
async def get_users(db: db_dependency):
    return db.query(Users).all()

@router.post('/', status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, create_user_request: CreateUserRequest):
    create_user_model = Users(
        email = create_user_request.email,
        username = create_user_request.username,
        firstname = create_user_request.firstname,
        lastname = create_user_request.lastname,
        hashedpassword = bcrypt_context.hash(create_user_request.password),
        role = create_user_request.role
    )
    db.add(create_user_model)
    db.commit()


@router.post('/token')
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                  db: db_dependency):
    user = authencate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail='Could not validata user.')
    token = create_access_token(user.username, user.id, timedelta(minutes=20))
    return token
