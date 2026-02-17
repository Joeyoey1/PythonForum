from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models import Entry, User, Reply, UserFollow
from playhouse.flask_utils import get_object_or_404, object_list
from markdown import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.extra import ExtraExtension
from markupsafe import Markup
import re

main = Blueprint('main', __name__)


def get_html_content(content):
    hilite = CodeHiliteExtension(linenums=False, css_class='highlight')
    extras = ExtraExtension()
    return Markup(markdown(content, extensions=[hilite, extras]))


@main.route('/')
def index():
    search_query = request.args.get('q')
    if search_query:
        query = Entry.select().where(
            (Entry.title.contains(search_query)) | (Entry.content.contains(search_query))
        )
        users = User.select().where(User.user_name.contains(search_query))
    else:
        query = Entry.select().where(Entry.published == True).order_by(Entry.timestamp.desc())
        users = User.select().where(User.id == -1)

    return object_list(
        'index.html',
        query,
        search=search_query,
        context_variable='post_list',
        check_bounds=False,
        user_list=users,
    )


@main.route('/drafts/')
@login_required
def drafts():
    query = Entry.select().where(
        (Entry.published == False) & (Entry.author == current_user.id)
    ).order_by(Entry.timestamp.desc())
    return object_list('index.html', query, context_variable='post_list', check_bounds=False, user_list=[])


@main.route('/create/', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        published = request.form.get('published') == 'y'

        if not title or not content:
            flash('Title and Content are required!', 'danger')
            return render_template('create.html', entry=Entry(title='', content=''))

        slug = re.sub(r'[^\w]+', '-', title.lower()).strip('-')
        entry = Entry.create(
            title=title,
            content=content,
            slug=slug,
            published=published,
            author=current_user.id,
        )
        flash('Entry created successfully!', 'success')
        return redirect(url_for('main.detail', slug=entry.slug) if published else url_for('main.edit', slug=entry.slug))

    return render_template('create.html', entry=Entry(title='', content=''))


@main.route('/<slug>/', methods=['GET', 'POST'])
def detail(slug):
    entry = get_object_or_404(Entry.select(), Entry.slug == slug)

    if request.method == 'POST':
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=url_for('main.detail', slug=slug)))
        content = request.form.get('content')
        if content:
            Reply.create(content=content, author=current_user.id, entry=entry.id)
            return redirect(url_for('main.detail', slug=entry.slug))

    replies = Reply.select().where(Reply.entry == entry)
    editable = current_user.is_authenticated and current_user.id == entry.author.id
    return render_template(
        'detail.html',
        entry=entry,
        entry_html_content=get_html_content(entry.content),
        replies=replies,
        editable=editable,
    )


@main.route('/<slug>/edit/', methods=['GET', 'POST'])
@login_required
def edit(slug):
    entry = get_object_or_404(Entry.select(), Entry.slug == slug)
    if current_user.id != entry.author.id:
        flash('You do not have permission to edit this entry.', 'danger')
        return redirect(url_for('main.detail', slug=entry.slug))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        if not title or not content:
            flash('Title and Content are required!', 'danger')
        else:
            entry.title = title
            entry.content = content
            entry.published = request.form.get('published') == 'y'
            entry.save()
            flash('Entry saved successfully!', 'success')
            return redirect(url_for('main.detail', slug=entry.slug) if entry.published else url_for('main.edit', slug=entry.slug))

    return render_template('edit.html', entry=entry, editable=True)


@main.route('/profile/')
@login_required
def profile():
    user = current_user
    entries = Entry.select().where(Entry.author == user.id)
    following = UserFollow.select().where(UserFollow.follower == user.id)
    followers = UserFollow.select().where(UserFollow.user == user.id)
    return render_template('profile.html', user=user, entries=entries, followers=followers, following=following)


@main.route('/profile/<name>')
def profile_other(name):
    user = User.get_or_none(User.user_name == name)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('main.index'))
    entries = Entry.select().where(Entry.author == user.id)
    following = UserFollow.select().where(UserFollow.follower == user.id)
    followers = UserFollow.select().where(UserFollow.user == user.id)
    return render_template('profile.html', user=user, entries=entries, followers=followers, following=following)


@main.route('/<name>/followers')
def followers(name):
    user = User.get_or_none(User.user_name == name)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('main.index'))
    rels = UserFollow.select().where(UserFollow.user == user.id)
    users = [rel.follower for rel in rels]
    return render_template('follower.html', user=user, followers=users)


@main.route('/<name>/following')
def following(name):
    user = User.get_or_none(User.user_name == name)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('main.index'))
    rels = UserFollow.select().where(UserFollow.follower == user.id)
    users = [rel.user for rel in rels]
    return render_template('following.html', user=user, following=users)
