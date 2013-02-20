gepulog-system
==============

blog system

SQLiteとFlaskによるブログシステムです。
$ python blog.py
で起動します。

settings.ini の編集により設定を変更できます。
username: 管理者のユーザ名
password: 管理者のパスワード（sha256でハッシュ化したもの）

sha256のハッシュ値を求める方法
$ echo -n password | sha256sum

host: 起動するIPアドレス
port: ポート番号
DEBUG: 開発用。運用時はFalseにする

このブログシステムは、sslによる運用が対応していないので、
パスワードは、平文で通信されます。注意願います。


データベースの初期化
$ python 
でpythonを起動したのち、
以下の二行を実行する。

import blog
blog.init_db()


gepulog systemには、
http://127.0.0.1:5000/
でアクセスできます。

ログイン方法は、
http://127.0.0.1:5000/login
にて、ユーザ名とパスワードを入力する。

ログアウト方法は、
http://127.0.0.1:5000/logout
にアクセスするだけです。

記事の新規投稿は、
http://127.0.0.1:5000/edit
にアクセスします。

編集は、
http://127.0.0.1:5000/edit/記事番号
です。

記事番号は、
http://127.0.0.1:5000/archives/記事番号
というように、訪問者がサイトを見る時の番号です。

記事の削除は、
http://127.9.9.1:5000/delete/記事番号
にアクセスします。

/edit, /delete は、ログインしていない状況でアクセスすると、
トップページにリダイレクトします。
