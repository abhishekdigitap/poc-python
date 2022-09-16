import math

from fastapi import FastAPI, Header
from typing import Union
from pydantic import BaseModel
import uuid
import datetime;

from sqlalchemy import Column, update, delete
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
app = FastAPI()
engine = create_engine("sqlite:///9.db", echo=True, future=True)


class User(Base):
    __tablename__ = "user_details"
    username = Column(String(30), primary_key=True)
    password = Column(String(30))


class Bloog(Base):
    __tablename__ = "blog_details"
    blog_id = Column(Integer, primary_key=True)
    blog_title = Column(String)
    blog_data = Column(String)
    username = Column(String, ForeignKey("user_details.username"))


class Sessions(Base):
    __tablename__ = "session_details"
    session_id = Column(String, primary_key=True)
    submisson_date = Column(String)
    username = Column(String, ForeignKey("user_details.username"))


Base.metadata.create_all(engine)


class UserSuccesfulCreation():
    def __init__(self, token, message):
        self.token = token
        self.message = message


class BlogContent(BaseModel):
    blog_title: str
    blog_data: str


class UserDetails(BaseModel):
    username: str
    password: str


class BlogDetails():
    def __init__(self, blog_id, blog_title, blog_data, created_by):
        self.blog_id = blog_id
        self.blog_title = blog_title
        self.blog_data = blog_data
        self.created_by = created_by


class Blog(BaseModel):
    blog_id: str
    blog_title: str
    blog_data: str


@app.post("/register")
async def register(userRegistration: UserDetails):
    if len(userRegistration.username) == 0 or len(userRegistration.password) == 0:
        return {"message": "username or password was empty"}
    Session = sessionmaker(bind=engine)
    session = Session()
    find = session.query(User).all()
    for row in find:
        if str(row.username) == str(userRegistration.username):
            return {"message": "Please try with some other username this already exists"}
        else:
            print(row)
    sessionId = str(uuid.uuid4());
    user = User(username=userRegistration.username, password=userRegistration.password)
    sessions = Sessions(session_id=sessionId, submisson_date=datetime.datetime.now().timestamp(),
                        username=userRegistration.username)
    session.add_all([user, sessions])
    session.commit()
    success = UserSuccesfulCreation(sessionId, "User creation Succesfull")
    return success


@app.get("/login")
async def login(userLogin: UserDetails):
    if len(userLogin.username) == 0 or len(userLogin.password) == 0:
        return {"message": "username or password was empty"}
    Session = sessionmaker(bind=engine)
    session = Session()
    find = session.query(User).filter_by(username=userLogin.username).first()
    if (find == None):
        return {"message": "No such user exists, Wrong email Id or password"}
    if str(find.username) == userLogin.username and str(find.password) == userLogin.password:
        sessionId = str(uuid.uuid4());
        sessions = Sessions(session_id=sessionId, submisson_date=datetime.datetime.now().timestamp(),
                            username=userLogin.username)
        session.add_all([sessions])
        session.commit()
        userCreated = UserSuccesfulCreation(sessionId, "Login Successful")
        return userCreated


def checkForTheSessionExpiration(time):
    if math.ceil(datetime.datetime.now().timestamp() - time) > 3000000000000000000000:
        return 1
    else:
        return 0


@app.post("/create/blog")
async def createBlog(blogData: BlogContent, token: Union[str, None] = Header(default=None)):
    if blogData.blog_data is None or len(blogData.blog_data) == 0 or len(blogData.blog_title) == 0:
        return {"message": "No content or title was found for the blog you created please add content"}
    Session = sessionmaker(bind=engine)
    session = Session()
    find = session.query(Sessions).filter_by(session_id=token).first()
    if (find == None):
        return {"message": "Wrong session Id"}
    flag = checkForTheSessionExpiration(float(find.submisson_date))
    if flag == 1:
        return {"message": "sessionExpired"}
    blog = Bloog(blog_title=blogData.blog_title, blog_data=blogData.blog_data,
                 username=str(find.username))
    session.add_all([blog])
    session.commit()
    return {"message": "Blog creation Successful"}


@app.get("/list/blog")
async def readBlog():
    Session = sessionmaker(bind=engine)
    session = Session()
    find = session.query(Bloog).all()
    if (find == None):
        return {"message": "No blogs are posted yet"}
    blogList = []
    for row in find:
        b = BlogDetails(str(row.blog_id), str(row.blog_title),
                        str(row.blog_data), str(row.username))
        blogList.append(b)
    return blogList


@app.get("/read/blog/")
async def readSpecificBlog(q: Union[str, None] = None):
    Session = sessionmaker(bind=engine)
    session = Session()
    if (q is None or len(q) == 0):
        return {"message": "query params missing"}
    find = session.query(Bloog).filter_by(blog_id=q).first()
    if (find is None):
        return {"message": "No such id exists"}
    return find


@app.put("/update/blog")
async def updateBlog(blog: Blog, token: Union[str, None] = Header(default=None)):
    if token is None or len(token) == 0:
        return {"message": "Invalid Token"}
    Session = sessionmaker(bind=engine)
    session = Session()
    find = session.query(Sessions).filter_by(session_id = token).first()
    if find is None:
        return {"message": "No such session id found"}
    flag = checkForTheSessionExpiration(float(find.submisson_date))
    if flag == 1:
        return {"message": "sessionExpired"}
    if blog.blog_id is None or blog.blog_title is None or blog.blog_data is None or len(blog.blog_id) == 0 or len(
            blog.blog_title) == 0 or len(blog.blog_data) == 0:
        return {"message": "Missing blog details"}
    findB = session.query(Bloog).filter_by(blog_id=blog.blog_id).first()
    if (findB == None):
        return {"message": "No such Blog Exists"}
    if str(find.username) != str(findB.username):
        return {"message": "You are unauthorized to update the blog"}
    session.query(Bloog).filter(Bloog.blog_id == blog.blog_id).update({Bloog.blog_data:blog.blog_data,Bloog.blog_title:blog.blog_title},synchronize_session = False)
    session.commit()
    return {"message": "Blog updation successfully"}


#
#
@app.delete("/delete/blog/")
async def deleteBlog(q: Union[str, None] = None, token: Union[str, None] = Header(default=None)):
    if token is None or len(token) == 0:
        return {"message": "Invalid Token"}
    Session = sessionmaker(bind=engine)
    session = Session()
    find = session.query(Sessions).filter_by(session_id = token).first()
    if find is None:
        return {"message": "No such session id found"}
    if q is None or len(q) == 0:
        return {"message": "missing query params"}
    flag = checkForTheSessionExpiration(float(find.submisson_date))
    if flag == 1:
        return {"message": "Session Expired"}
    findB = session.query(Bloog).filter_by(blog_id=int(q)).first()
    if findB == None:
        return {"message": "No such Blog Exists"}
    if (str(findB.username) != str(find.username)):
        return {"message": "You are unauthorized to delete the blog"}
    session.query(Bloog).filter(Bloog.blog_id == q).delete(synchronize_session=False)
    session.commit()
    return {"message": "Delete Successful"}
