#!/usr/bin/python
# -*- coding:utf-8 -*-

# gepulog system

# The MIT License

# Copyright (c) 2012-2013 gepuro

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


# To do
# 画像アップロードの改良 file apiとか使いたいね
# githubにアップする (ソーシャルボタンやgoogleカスタム検索を消しておく or 追加しやすい工夫をしておく(設定ファイル?,ドキュメント?))

import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, jsonify, make_response
import cPickle as pickle
import markdown
import datetime
import os
import glob
from werkzeug import secure_filename
from contextlib import closing
import ConfigParser
import hashlib

# configuration
CONFIG_FILE = 'settings.ini'
conf = ConfigParser.SafeConfigParser()
conf.read(CONFIG_FILE)
USERNAME = conf.get('credential', 'username')
PASSWORD = conf.get('credential', 'password')
host = conf.get('options','host')
port     = conf.get('options','port')
DEBUG = False

SECRET_KEY = 'cc8d8183d8e0fe9debb619ddd5b8fa5a'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif', 'JPG'])
DATABASE = "./db/gepulog.db"
UPLOAD_FOLDER= "./image"

# create out little application
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config.from_object(__name__)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    pickle.dump({}, open("./db/sidebar.dat","w"))
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    g.db.close()

@app.route('/javascript/<filename>')
def javascript(filename):
    return open('./javascript/' + filename).read()

@app.route('/image/<filename>')
def image(filename):
    response = make_response(open(UPLOAD_FOLDER + '/' + filename).read())
    response.headers['Content-Type'] = 'image/jpeg'
    return response

def notation(text):
    html =  markdown.markdown(text, ['tables'])
    html = html.replace("<table>", "<table class='table'>")
    html = html.replace("<h3>", '<h3 style="border-left:solid 3px blue;"">')
    html = html.replace("<h4>", '<h4 style="border-left:solid 3px blue;"">')
    return html

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

class Base:
    def __init__(self,use_g=True):
        if use_g:
            self.g = g
        try:
            self.sidebar_db = pickle.load(open("./db/sidebar.dat"))
        except:
            sidebar_db = {}
    def page_condition(self,page):
        if page <= 0:
            page = 1
        return page
    def start_page(self,show_artcile,page):
        page = self.page_condition(page)
        return ( page - 1 ) * show_artcile
    def page_info(self,show_artcile,page,articles_len,name="page",category=""):
        pagination = {}
        page = self.page_condition(page)
        if category == "":
            pagination["older"] = "/" + name + "/" + str(page+1)
            pagination["newer"] = "/" + name + "/" + str(page-1)
        else:
            pagination["older"] = "/" + "category" + "/" + category + "/" + str(page+1)
            pagination["newer"] = "/" + "category" + "/" + category + "/" + str(page-1)

        pagination["recentry"] = page in [0,1]
        pagination["last"] = articles_len != show_artcile # 最後のページかどうか
        return pagination
    def article(self,show_artcile=10,page=1):
        try:
            page = self.page_condition(page)
            start = self.start_page(show_artcile,page)
            cur = self.g.db.execute('select * from article order by id desc limit ' + str(show_artcile) + ' offset ' + str(start) )
            articles = [dict(id=row[0], title=row[1], date_time=row[2],
                             category=row[3].split(","), contents=notation(row[4]))
                        for row in cur.fetchall()]
            return articles
        except:
            return []
    def article_specified_id(self,aid=[]):
        articles = []
        try:
            for i in reversed(aid):
                cur = g.db.execute('select * from article where id = ' + str(i) )
                articles += [dict(id=row[0], title=row[1], date_time=row[2],
                                  category=row[3].split(","), contents=notation(row[4]))
                             for row in cur.fetchall()]
            return articles
        except:
            return []
    def article_newest_aid(self):
        return int(self.g.db.execute("select max(id) from article").fetchone()[0])
    def article_remove(self,aid):
        try:
            self.g.db.execute('delete from article where id = ' + str(aid))
        except Exception, e:
            print e
            if self.g.db:
                self.g.db.rollback()
        finally:
            self.g.db.commit()
    def article_add(self,aid,title,date_time,category,contents):
        try:
            if aid == 0:
                self.g.db.execute('insert or replace into article (title, date_time, category, contents) values (?, ?, ?, ?)',
                                  [title, date_time, category, contents])
            else:
                self.g.db.execute('delete from article where id= ' + str(aid))
                self.g.db.execute('insert or replace into article (id, title, date_time, category, contents) values (?, ?, ?, ?, ?)',
                                  [int(aid), title, date_time, category, contents])
        except Exception,e:
            print e
            if self.g.db:
                self.g.db.rollback()
        finally:
            self.g.db.commit()
    def category_remake(self):
        category_db = {"category":{}}
        with closing(connect_db()) as db:
            cur = db.execute('select id,category from article')
            articles = [dict(id=row[0], category=row[1].split(",")) for row in cur.fetchall()]
            for article in articles:
                for c in article["category"]:
                    if c != "":
                        category_db["category"].setdefault(c,[])
                        category_db["category"][c].append(int(article["id"]))
        category_db["category_num"] = [dict(cate=c, num=len(category_db["category"][c]))
                                       for c in category_db["category"].keys()]
        return category_db
    def recentry_remake(self):
        recentry_db = []
        with closing(connect_db()) as db:
            cur = db.execute('select id,title from article order by id desc limit 10')
            for row in cur.fetchall():
                recentry_db.append({"id":int(row[0]),"title":row[1]})
        return recentry_db
    def sidebar_remake(self):
        sidebar_db = {}
        category_db = self.category_remake()
        sidebar_db["category"] = category_db["category"]
        sidebar_db["category_num"] = category_db["category_num"]
        sidebar_db["recentry"] = self.recentry_remake()
        self.sidebar_db = sidebar_db
        pickle.dump(sidebar_db, open("./db/sidebar.dat","w"))

@app.route('/', defaults={"page":1})
@app.route('/page/<int:page>')
def toppage(page):
    base = Base()
    show_artcile = 10 # 一ページに何件の記事を表示させるか
    articles = base.article(show_artcile=10,page=page)
    if len(articles) == 0:
        abort(404)
    return render_template('index.html',
                           articles = articles,
                           categories = base.sidebar_db["category_num"],
                           recentries = base.sidebar_db["recentry"],
                           pagination = base.page_info(show_artcile, page, len(articles)),
                           title="gepulog")

@app.route('/archives/<int:aid>')
def archives(aid):
    base = Base()
    articles = base.article_specified_id([aid])
    if len(articles) == 0:
        abort(404)
    return render_template('archive.html',
                           articles = articles,
                           categories = base.sidebar_db["category_num"],
                           recentries = base.sidebar_db["recentry"],
                           aid = aid,
                           title = articles[0]["title"] + " - gepulog")

@app.route('/category/<category>', defaults={"page":1})
@app.route('/category/<category>/<int:page>')
def category_page(category, page):
    show_artcile = 10 # 一ページに何件の記事を表示させるか
    base = Base()
    start = base.start_page(show_artcile,page)
    try:
        aid = base.sidebar_db["category"][category][::-1][start:(start+show_artcile)]
    except:
        abort(404)
    aid.reverse()
    articles = base.article_specified_id(aid)
    if len(articles) == 0:
        abort(404)
    return render_template('index.html',
                           articles = articles,
                           categories = base.sidebar_db["category_num"],
                           recentries = base.sidebar_db["recentry"],
                           pagination = base.page_info(show_artcile, page, len(articles), category=category),
                           active_category = category,
                           title = category + " - gepulog")

@app.route('/list', defaults={"page":1})
@app.route('/list/<int:page>')
def listp(page):
    base = Base()
    show_artcile = 50 # 一ページに何件の記事を表示させるか
    articles = base.article(show_artcile, page)
    if len(articles) == 0:
        abort(404)
    return render_template('list.html',
                           articles = articles,
                           categories = base.sidebar_db["category_num"],
                           recentries = base.sidebar_db["recentry"],
                           pagination = base.page_info(show_artcile, page, len(articles), name="list"),
                           title=u"記事一覧 - gepulog")

@app.route('/robots.txt')
def robots():
    return ""

# 外部API
@app.route('/list_api')
def list_api():
    base = Base()
    show_artcile = 5
    articles = base.article(show_artcile)
    if len(articles) == 0:
        return jsonify(result = "{}")
    else:
        return jsonify(result = articles)


# 以下 編集者用
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if session.get("logged_in"):
        return redirect(url_for('toppage'))
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password']).hexdigest()
        if username != app.config['USERNAME']:
            error = 'Invalid username'
        elif password != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            return redirect(url_for('toppage'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('toppage'))

@app.route('/edit', methods=['GET', 'POST'], defaults={"aid":0})
@app.route('/edit/<int:aid>', methods=['GET', 'POST'])
def edit(aid):
    # aid == 0 は、新規作成・その他は、編集
    base = Base()
    if session.get("logged_in", False) == False:
        return redirect(url_for('toppage'))
    elif request.method == "POST":
        aid = int(request.form["Aid"])
        title = request.form["Title"]
        category = request.form["Category"]
        contents = request.form["Contents"]
        date_time = request.form["Date_Time"]
        if date_time == "":
            d = datetime.datetime.today()
            date_time = d.strftime("%Y-%m-%d %H:%M:%S")
        if title == "" or contents == "":    # タイトルとか本文がなかったら、戻らせる
            article = {"id":aid, "title":title, "data_time":date_time, "category":category, "contents":contents}
            return render_template('edit.html', article = article)
        base.article_add(aid,title,date_time,category,contents)
        if aid == 0:
            aid = base.article_newest_aid()
        base.sidebar_remake()
        return redirect(url_for("toppage"))
    
    if aid == 0:
        article = {"id":0, "title":"", "data_time":"", "category":"", "contents":""}
    else:
        cur = g.db.execute('select * from article where id = ' + str(aid) )
        article = [dict(id=row[0], title=row[1], date_time=row[2],category=row[3], contents=row[4])
                    for row in cur.fetchall()][0]

    return render_template('edit.html', article = article, title = "gepulog - edit")

@app.route('/delete/<int:aid>')
def delete(aid):
    if session.get("logged_in", False) == False:
        return redirect(url_for('toppage'))
    base = Base(use_g=True)
    base.article_remove(aid)
    base.sidebar_remake()
    return redirect(url_for('toppage'))

@app.route('/preview')
def preview():
    if session.get("logged_in", False) == False:
        return redirect(url_for('toppage'))
    contents = notation(request.args.get("contents",""))
    return jsonify(result=contents)

@app.route("/upload", methods=['GET', 'POST'])
def upload_file():
    if session.get("logged_in", False) == False:
        return redirect(url_for('toppage'))
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('upload_file', filename=filename))
    filelist = glob.glob(UPLOAD_FOLDER + "/*")
    return render_template('upload.html', filelist = filelist, title="Upload new File")

if __name__ == '__main__':
    app.run(host=host, port=int(port))
