from flask import Blueprint, render_template
from flask_login import login_required

content_bp = Blueprint('content', __name__)

@content_bp.route('/feed')
@login_required
def feed():
    return render_template('feed.html', posts=[])

@content_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_post():
    return render_template('create_post.html')