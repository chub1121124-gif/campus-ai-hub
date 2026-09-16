from flask import (
    Blueprint,
    jsonify,
    request,
    session
)

from extensions import db
from models import Post
from .auth import login_required


announcement_bp = Blueprint(
    "announcement",
    __name__,
    url_prefix="/api/posts"
)


def serialize_post(post):
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "category": post.category,
        "is_ai_priority": post.is_ai_priority,
        "author_id": post.author_id,

        "author_name": (
            post.author.full_name
            if post.author else "未知"
        ),

        "created_at": (
            post.created_at.strftime(
                "%Y-%m-%d %H:%M"
            )
            if post.created_at else None
        )
    }


@announcement_bp.route("", methods=["GET"])
@login_required
def get_posts():
    keyword = request.args.get(
        "q",
        ""
    ).strip()

    category = request.args.get(
        "category",
        ""
    ).strip()

    query = Post.query

    if keyword:
        query = query.filter(
            db.or_(
                Post.title.contains(keyword),
                Post.content.contains(keyword)
            )
        )

    if category:
        query = query.filter(
            Post.category == category
        )

    posts = (
        query
        .order_by(Post.created_at.desc())
        .all()
    )

    return jsonify({
        "success": True,
        "data": [
            serialize_post(post)
            for post in posts
        ]
    })


@announcement_bp.route("", methods=["POST"])
@login_required
def create_post():
    data = request.get_json(silent=True) or request.form

    title = str(
        data.get("title", "")
    ).strip()

    content = str(
        data.get("content", "")
    ).strip()

    category = str(
        data.get("category", "一般資訊")
    ).strip()

    is_ai_priority = data.get(
        "is_ai_priority",
        False
    )

    if not title:
        return jsonify({
            "success": False,
            "message": "請輸入標題"
        }), 400

    if not content:
        return jsonify({
            "success": False,
            "message": "請輸入內容"
        }), 400

    post = Post(
        title=title,
        content=content,
        category=category,
        is_ai_priority=bool(is_ai_priority),
        author_id=session["user_id"]
    )

    db.session.add(post)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "資訊新增成功",
        "data": serialize_post(post)
    })


@announcement_bp.route(
    "/<int:post_id>",
    methods=["PUT"]
)
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)

    user_id = session["user_id"]

    from models import User

    user = db.session.get(
        User,
        user_id
    )

    if (
        post.author_id != user_id
        and user.role != "admin"
    ):
        return jsonify({
            "success": False,
            "message": "沒有修改權限"
        }), 403

    data = request.get_json(silent=True) or request.form

    post.title = str(
        data.get("title", post.title)
    ).strip()

    post.content = str(
        data.get("content", post.content)
    ).strip()

    post.category = str(
        data.get(
            "category",
            post.category
        )
    ).strip()

    if "is_ai_priority" in data:
        post.is_ai_priority = bool(
            data.get("is_ai_priority")
        )

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "資訊修改成功",
        "data": serialize_post(post)
    })


@announcement_bp.route(
    "/<int:post_id>",
    methods=["DELETE"]
)
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)

    user_id = session["user_id"]

    from models import User

    user = db.session.get(
        User,
        user_id
    )

    if (
        post.author_id != user_id
        and user.role != "admin"
    ):
        return jsonify({
            "success": False,
            "message": "沒有刪除權限"
        }), 403

    db.session.delete(post)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "資訊已刪除"
    })