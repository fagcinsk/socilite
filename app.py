#!/usr/bin/env python

from datetime import datetime

from flask import Flask, g, redirect, render_template
from flask.helpers import url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from pony.flask import Pony
from pony.orm.core import db_session, flush

from forms import LoginForm, MessageForm, RegisterForm
from models import Message, User, db

app = Flask(__name__)
app.config.update(dict(
    DEBUG=False,
    SECRET_KEY='my_$3cr37',
    PONY={
        'provider': 'sqlite',
        'filename': 'db.sqlite',
        'create_db': True
    }
))


@app.route('/')
def index():
    return render_template('index.html', users=User.select())


@app.route('/add_friend/<login>')
def add_friend(login):
    current_user.friends.add(User.get(login=login))
    return redirect('/')


@app.route('/remove_friend/<login>')
def remove_friend(login):
    current_user.friends.remove(User.get(login=login))
    return redirect('/')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.get(login=form.login.data)
        user.last_login = datetime.now()
        login_user(user)
        return redirect('/')

    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def reg():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            login=form.login.data,
            password=form.password.data,
            first_name=form.first_name.data
        )
        user.last_login = datetime.now()
        flush()
        login_user(user)
        return redirect('/')

    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.route('/messages/<login>', methods=['GET', 'POST'])
@login_required
def messages(login):
    dst = User.get(login=login)
    form = MessageForm()
    if form.validate_on_submit():
        Message(src=current_user, dst=dst, text=form.text.data)
        return redirect(url_for('messages', login=login))

    messages = Message.select(
        lambda m:
        (m.dst == dst and m.src == current_user)
        or
        (m.src == dst and m.dst == current_user)
    ).order_by(lambda m: m.created_at)
    return render_template('messages.html', messages=messages, form=form)


@app.before_request
@db_session
def _load_user():
    g.user = current_user


if __name__ == '__main__':
    db.bind(**app.config['PONY'])
    db.generate_mapping(create_tables=True)
    Pony(app)
    login_manager = LoginManager(app)
    login_manager.login_view = 'login'

    with db_session:
        if User.select().count() == 0:
            for i in range(1, 4):
                User(first_name='User %d' %
                     i, login='user%d' % i, password='123')

    @login_manager.user_loader
    def load_user(user_id):
        return User.get(id=user_id)

    app.run(host='0.0.0.0')
