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
    session = Session(engine)
    stmt = select(User.username)
    find = session.scalars(stmt)
    for row in find:
        if str(row) == str(userRegistration.username):
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
    session = Session(engine)
    stmt = select(User).where(User.username == str(userLogin.username))
    find = session.execute(stmt).fetchone()
    if (find == None):
        return {"message": "No such user exists, Wrong email Id or password"}
    if str(getattr(find[0], 'username')) == userLogin.username and str(
            getattr(find[0], 'password')) == userLogin.password:
        sessionId = str(uuid.uuid4());
        sessions = Sessions(session_id=sessionId, submisson_date=datetime.datetime.now().timestamp(),
                            username=userLogin.username)
        session.add_all([sessions])
        session.commit()
        userCreated = UserSuccesfulCreation(sessionId, "Login Successful")
        return userCreated


def checkForTheSessionExpiration(time):
    if math.ceil(datetime.datetime.now().timestamp() - time) > 3000000000000000000000000:
        return 1
    else:
        return 0


@app.post("/create/blog")
async def createBlog(blogData: BlogContent, token: Union[str, None] = Header(default=None)):
    if blogData.blog_data is None or len(blogData.blog_data) == 0 or len(blogData.blog_title) == 0:
        return {"message": "No content or title was found for the blog you created please add content"}
    session = Session(engine)
    stmt = select(Sessions).where(Sessions.session_id == str(token))
    find = session.execute(stmt).fetchone()
    if (find == None):
        return {"message": "Wrong session Id"}
    flag = checkForTheSessionExpiration(float(getattr(find[0], 'submisson_date')))
    if flag == 1:
        return {"message": "sessionExpired"}
    blog = Bloog(blog_title=blogData.blog_title, blog_data=blogData.blog_data,
                 username=str(getattr(find[0], 'username')))
    session.add_all([blog])
    session.commit()
    return {"message": "Blog creation Successful"}


@app.get("/list/blog")
async def readBlog():
    session = Session(engine)
    stmt = select(Bloog)
    find = session.execute(stmt)
    if (find == None):
        return {"message": "No blogs are posted yet"}
    blogList = []
    for row in find:
        b = BlogDetails(str(getattr(row[0], 'blog_id')), str(getattr(row[0], 'blog_title')),
                        str(getattr(row[0], 'blog_data')), str(getattr(row[0], 'username')))
        blogList.append(b)
    return blogList


@app.get("/read/blog/")
async def readSpecificBlog(q: Union[str, None] = None):
    session = Session(engine)
    print(len(q))
    if (q is None or len(q) == 0):
        return {"message": "query params missing"}
    stmt = select(Bloog).where(Bloog.blog_id == int(q))
    find = session.execute(stmt).fetchone()
    if (find is None or len(find) == 0):
        return {"message": "No such id exists"}
    return find


@app.put("/update/blog")
async def updateBlog(blog: Blog, token: Union[str, None] = Header(default=None)):
    if token is None or len(token) == 0:
        return {"message": "Invalid Token"}
    session = Session(engine)
    stmt = select(Sessions).where(Sessions.session_id == token)
    find = session.execute(stmt).fetchone()
    if find is None:
        return {"message": "No such session id found"}
    flag = checkForTheSessionExpiration(float(getattr(find[0], 'submisson_date')))
    if flag == 1:
        return {"message": "sessionExpired"}
    if blog.blog_id is None or blog.blog_title is None or blog.blog_data is None or len(blog.blog_id) == 0 or len(
            blog.blog_title) == 0 or len(blog.blog_data) == 0:
        return {"message": "Missing blog details"}
    stmt = select(Bloog).where(Bloog.blog_id == (int(blog.blog_id)))
    findB = session.execute(stmt).fetchone()
    if (findB == None):
        return {"message": "No such Blog Exists"}
    if (str(getattr(findB[0], 'username')) != str(getattr(find[0], 'username'))):
        return {"message": "You are unauthorized to update the blog"}
    stmt = update(Bloog).where(Bloog.blog_id == int(blog.blog_id)).values(blog_data=blog.blog_data,
                                                                          blog_title=blog.blog_title)
    session.execute(stmt)
    session.commit()
    return {"message": "Blog updation successfully"}


#
#
@app.delete("/delete/blog/")
async def deleteBlog(q: Union[str, None] = None, token: Union[str, None] = Header(default=None)):
    if token is None or len(token) == 0:
        return {"message": "Invalid Token"}
    session = Session(engine)
    stmt = select(Sessions).where(Sessions.session_id == token)
    find = session.execute(stmt).fetchone()
    if find is None:
        return {"message": "No such session id found"}
    if q is None or len(q) == 0:
        return {"message": "missing query params"}
    flag = checkForTheSessionExpiration(float(getattr(find[0], 'submisson_date')))
    if flag == 1:
        return {"message": "Session Expired"}
    stmt = select(Bloog).where(Bloog.blog_id == int(q))
    findB = session.execute(stmt).fetchone()
    if (findB == None):
        return {"message": "No such Blog Exists"}
    if (str(getattr(findB[0], 'username')) != str(getattr(find[0], 'username'))):
        return {"message": "You are unauthorized to delete the blog"}
    stmt = delete(Bloog).where(Bloog.blog_id == int(q))
    session.execute(stmt)
    session.commit()
    return {"message": "Delete Successful"}
