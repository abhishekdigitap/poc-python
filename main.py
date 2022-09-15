import math
import traceback

from fastapi import FastAPI, Header
import sqlite3
from typing import Union
from pydantic import BaseModel
import uuid
import datetime;

app = FastAPI()
conn = sqlite3.connect('6.db')

query = ('''create table if not exists user_details
            (username text primary key,
            password text)''')
conn.execute(query)
query = ('''create table if not exists blog_details
            (blogId integer primary key AUTOINCREMENT,
            blog_title text,
            blog_data text,
            username text,
            foreign key(username) references user_details(username))''')
conn.execute(query)
query = ('''create table if not exists session_details
            (username text,
            session_id primary key,
            SubmissionDate text,
            foreign key(username) references user_details(username))''')
conn.execute(query)


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
        self.blog_id= blog_id
        self.blog_title= blog_title
        self.blog_data= blog_data
        self.created_by= created_by

class Blog(BaseModel):
    blog_id:str
    blog_title:str
    blog_data: str



@app.post("/register")
async def register(userRegistration: UserDetails):
    if len(userRegistration.username) == 0 or userRegistration.password == 0 :
        return {"message":"username or password was empty"}
    try:
        conn.execute("""insert into user_details values(?,?)""", (userRegistration.username, userRegistration.password))
        sessionId = str(uuid.uuid4());
        try:
            conn.execute("""insert into session_details values(?,?,?)""",
                         (userRegistration.username, sessionId, datetime.datetime.now().timestamp()))
            userCreated = UserSuccesfulCreation(sessionId, "User creation sucessful")
            conn.commit()
            return userCreated
        except sqlite3.IntegrityError as e:
            print(traceback.print_exc())
    except sqlite3.IntegrityError as e:
        return {"errorLog": "Please try with some other username this already exists"}


@app.get("/login")
async def login(userLogin: UserDetails):
    try:
        res = conn.execute("""select * from user_details where username = ? and password = ?""",
                           (userLogin.username, userLogin.password))
        if (len(res.fetchall()) == 0):
            return {"message": "No such user exists, Wrong email Id or password"}
        else:
            sessionId = str(uuid.uuid4());
            try:
                conn.execute("""insert into session_details values(?,?,?)""",
                             (userLogin.username, sessionId, datetime.datetime.now().timestamp()))
                conn.commit()
                userCreated = UserSuccesfulCreation(sessionId, "Login Successful")
                return userCreated
            except sqlite3.IntegrityError as e:
                print(traceback.print_exc())
    except sqlite3.IntegrityError as e:
        print(traceback.print_exc())


def checkForTheSessionExpiration(time):
    if (math.ceil(datetime.datetime.now().timestamp() - time) > 1000000000000000000000):
        return 1
    else:
        return 0


@app.post("/create/blog")
async def createBlog(blogData: BlogContent, token: Union[str, None] = Header(default=None)):
    res = conn.execute("""select * from session_details where session_id=?""", [token])
    find = res.fetchone()
    if find is None or len(find) == 0:
        return {"message": "No such session Id found"}
    flag = checkForTheSessionExpiration(float(find[2]))
    if flag == 1:
        return {"message": "sessionExpired"}
    if blogData.blog_data is None or len(blogData.blog_data) == 0 or len(blogData.blog_title) == 0:
        return {"message": "No content or title was found for the blog you created please add content"}
    conn.execute("""insert into blog_details(blog_title,blog_data,username) values(?,?,?)""", (blogData.blog_title,blogData.blog_data, find[0]))
    conn.commit()
    return {"message": "Blog creation Successful"}

@app.get("/list/blog")
async def readBlog():
    res = conn.execute("""select * from blog_details""")
    find = res.fetchall()
    if find is None or len(find) == 0 :
        return {"message":"No blogs are posted yet"}
    blogList = []
    for row in find:
        print(row[0],row[1],row[2],row[3])
        b = BlogDetails(str(row[0]),str(row[1]),str(row[2]),str(row[3]));
        blogList.append(b);
    return blogList

@app.get("/read/blog/")
async def readSpecificBlog(q: Union[str, None] = None):
    if(q is None):
        return {"message": "query params missing"}
    res = conn.execute("""select * from blog_details where blogId = ?""",[int(q)])
    find = res.fetchone();
    if(find is None or len(find) == 0):
        return {"message":"No such id exists"}
    blogDetails = BlogDetails(find[0],find[1],find[2],find[3])
    return blogDetails

@app.put("/update/blog")
async def updateBlog(blog:Blog,token: Union[str, None] = Header(default=None)):
    if token is None or len(token)==0:
        return {"message":"Invalid Token"}
    res = conn.execute("""select * from session_details where session_id=?""",[token])
    find = res.fetchone()
    if find is None or len(find)==0:
        return {"message":"No such session id found"}
    time = float(find[2])
    flag = checkForTheSessionExpiration(time)
    if flag == 1:
        return {"message":"Session Expired"}
    if blog.blog_id is None or blog.blog_title is None or blog.blog_data is None or len(blog.blog_id) == 0 or len(blog.blog_title) == 0 or len(blog.blog_data) == 0:
        return {"message":"Missing blog details"}
    res = conn.execute("""select * from blog_details where blogId = ?""",[int(blog.blog_id)])
    findB = res.fetchone()
    if(str(findB[3]) != str(find[0])):
        return {"message":"You are unathorized to update the blog"}
    try:
        conn.execute("""update blog_details set blog_title = ?,blog_data = ? where blogId = ?""",(blog.blog_title,blog.blog_data,int(blog.blog_id)))
        conn.commit();
        return {"message":"Blog updation successfully"}
    except sqlite3.IntegrityError as e:
        return {"message":"Error occurred"}

@app.delete("/delete/blog/")
async def deleteBlog(q: Union[str, None] = None,token: Union[str, None] = Header(default=None)):
    if token is None or len(token)==0:
        return {"message":"Invalid Token"}
    res = conn.execute("""select * from session_details where session_id=?""",[token])
    find = res.fetchone()
    if find is None or len(find)==0:
        return {"message":"No such session id found"}
    if q is None or len(q)==0:
        return {"message":"missing query params"}
    time = float(find[2])
    flag = checkForTheSessionExpiration(time)
    if flag == 1:
        return {"message":"Session Expired"}
    res = conn.execute("""select * from blog_details where blogId = ?""", [int(q)])
    findB = res.fetchone()
    if (str(findB[3]) != str(find[0])):
        return {"message": "You are unathorized to update the blog"}
    try:
        conn.execute("delete from blog_details where blogId = ?",[int(q)])
        conn.commit()
        return {"message":"Delete Successful"}
    except sqlite3.IntegrityErrore as e:
        return {"message":"Error occurred"}

