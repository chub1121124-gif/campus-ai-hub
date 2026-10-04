import os
import uuid

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
    send_from_directory
)

from werkzeug.utils import secure_filename

from extensions import db

from models import (
    Community,
    CommunityMember,
    CommunityJoinRequest,
    CommunityMessage,
    User
)

from .auth import login_required

from services.community_service import (
    create_community_for_user,
    find_communities,
    get_joined_community_ids,
    join_community_for_user,
)

from utils.auth_helpers import get_logged_in_user


community_bp = Blueprint(
    "community",
    __name__,
    url_prefix="/communities"
)


# =========================================================
# 聊天室附件允許格式
# =========================================================

ALLOWED_CHAT_EXTENSIONS = {
    # 圖片
    "png", "jpg", "jpeg", "gif", "webp",

    # 文件
    "pdf", "doc", "docx",
    "ppt", "pptx",
    "xls", "xlsx",
    "txt", "csv",

    # 壓縮檔
    "zip", "rar", "7z",

    # 影音
    "mp4", "webm", "mov",
    "mp3", "wav", "m4a", "ogg",

    # 程式碼
    "py", "java", "cpp", "c",
    "js", "html", "css", "json"
}


IMAGE_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp"
}


# =========================================================
# 共用函式
# =========================================================

def is_community_member(
    community,
    user_id
):
    if community.creator_id == user_id:
        return True

    membership = (
        CommunityMember.query
        .filter_by(
            community_id=community.id,
            user_id=user_id
        )
        .first()
    )

    return membership is not None


def allowed_chat_file(filename):

    if "." not in filename:
        return False

    extension = (
        filename
        .rsplit(".", 1)[1]
        .lower()
    )

    return (
        extension in
        ALLOWED_CHAT_EXTENSIONS
    )


# =========================================================
# 社團首頁
# =========================================================

@community_bp.route("/")
@login_required
def community_page():

    user = get_logged_in_user()

    keyword = request.args.get(
        "q",
        ""
    ).strip()

    filter_type = request.args.get(
        "filter",
        "all"
    )

    communities = find_communities(
        keyword,
        filter_type
    )

    joined_ids = (
        get_joined_community_ids(
            user.id
        )
    )

    return render_template(
        "communities.html",
        current_user=user,
        communities=communities,
        joined_ids=joined_ids
    )


# =========================================================
# 建立社團
# =========================================================

@community_bp.route(
    "/create",
    methods=["POST"]
)
@login_required
def create_community():

    user = get_logged_in_user()

    try:

        create_community_for_user(
            user_id=user.id,

            name=request.form.get(
                "name",
                ""
            ).strip(),

            description=request.form.get(
                "description",
                ""
            ).strip(),

            community_type=request.form.get(
                "community_type",
                "group"
            ),

            join_mode=request.form.get(
                "join_mode",
                "open"
            ),

            password=request.form.get(
                "password",
                ""
            ).strip()
        )

    except ValueError as error:

        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    return jsonify({
        "success": True,
        "message": "建立成功"
    })


# =========================================================
# 加入社團
# =========================================================

@community_bp.route(
    "/<int:community_id>/join",
    methods=["POST"]
)
@login_required
def join_community(
    community_id
):

    user = get_logged_in_user()

    community = (
        Community.query
        .get_or_404(
            community_id
        )
    )

    result = join_community_for_user(
        community=community,
        user_id=user.id,

        password=request.form.get(
            "password",
            ""
        ).strip()
    )

    result_map = {

        "already_joined": (
            False,
            "你已經加入",
            400
        ),

        "wrong_password": (
            False,
            "加入密碼錯誤",
            400
        ),

        "already_requested": (
            False,
            "申請已送出，等待建立者審核",
            400
        ),

        "requested": (
            True,
            "申請已送出，等待建立者審核",
            200
        ),

        "joined": (
            True,
            "加入成功",
            200
        ),
    }

    if result not in result_map:

        return jsonify({
            "success": False,
            "message": "未知加入狀態"
        }), 500

    success, message, status_code = (
        result_map[result]
    )

    return jsonify({
        "success": success,
        "message": message
    }), status_code


# =========================================================
# 社團詳細頁
# =========================================================

@community_bp.route(
    "/<int:community_id>"
)
@login_required
def community_detail(
    community_id
):

    current_user_id = (
        session.get("user_id")
    )

    community = (
        Community.query
        .get_or_404(
            community_id
        )
    )

    membership = (
        CommunityMember.query
        .filter_by(
            community_id=community_id,
            user_id=current_user_id
        )
        .first()
    )

    is_creator = (
        community.creator_id ==
        current_user_id
    )

    if (
        not membership
        and not is_creator
    ):

        return redirect(
            url_for(
                "community.community_page"
            )
        )

    members = (
        CommunityMember.query
        .filter_by(
            community_id=community_id
        )
        .all()
    )

    messages = (
        CommunityMessage.query
        .filter_by(
            community_id=community_id
        )
        .order_by(
            CommunityMessage
            .created_at
            .asc()
        )
        .all()
    )

    current_user = (
        db.session.get(
            User,
            current_user_id
        )
    )

    return render_template(
        "community_detail.html",

        community=community,
        membership=membership,
        members=members,
        messages=messages,

        current_user=current_user,
        is_creator=is_creator
    )


# =========================================================
# 傳送純文字訊息
# =========================================================

@community_bp.route(
    "/<int:community_id>/messages",
    methods=["POST"]
)
@login_required
def send_community_message(
    community_id
):

    current_user_id = (
        session.get("user_id")
    )

    community = (
        Community.query
        .get_or_404(
            community_id
        )
    )

    if not is_community_member(
        community,
        current_user_id
    ):

        return jsonify({
            "success": False,
            "message":
                "你不是此社群成員"
        }), 403

    data = (
        request.get_json(
            silent=True
        )
        or request.form
    )

    content = str(
        data.get(
            "content",
            ""
        )
    ).strip()

    if not content:

        return jsonify({
            "success": False,
            "message": "請輸入訊息"
        }), 400

    message = CommunityMessage(
        community_id=community_id,
        sender_id=current_user_id,
        message_type="text",
        content=content
    )

    try:

        db.session.add(
            message
        )

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        return jsonify({
            "success": False,
            "message":
                f"訊息傳送失敗：{error}"
        }), 500

    return jsonify({
        "success": True,
        "message": "訊息已送出"
    })


# =========================================================
# 上傳聊天室附件
# =========================================================

@community_bp.route(
    "/<int:community_id>/messages/upload",
    methods=["POST"]
)
@login_required
def upload_community_file(
    community_id
):

    current_user_id = (
        session.get("user_id")
    )

    community = (
        Community.query
        .get_or_404(
            community_id
        )
    )

    if not is_community_member(
        community,
        current_user_id
    ):

        return jsonify({
            "success": False,
            "message":
                "你不是此社群成員"
        }), 403

    file = request.files.get(
        "file"
    )

    if (
        not file
        or not file.filename
    ):

        return jsonify({
            "success": False,
            "message":
                "請選擇要上傳的檔案"
        }), 400

    if not allowed_chat_file(
        file.filename
    ):

        return jsonify({
            "success": False,
            "message":
                "不支援此檔案格式"
        }), 400

    original_name = (
        secure_filename(
            file.filename
        )
    )

    extension = (
        original_name
        .rsplit(".", 1)[1]
        .lower()
    )

    stored_name = (
        f"{uuid.uuid4().hex}."
        f"{extension}"
    )

    # app.py 已有 COMMUNITY_UPLOAD_FOLDER
    upload_folder = (
        current_app.config.get(
            "COMMUNITY_UPLOAD_FOLDER"
        )
    )

    if not upload_folder:

        upload_folder = os.path.join(
            current_app.static_folder,
            "uploads",
            "community"
        )

    os.makedirs(
        upload_folder,
        exist_ok=True
    )

    file_path = os.path.join(
        upload_folder,
        stored_name
    )

    try:

        file.save(
            file_path
        )

        file_url = url_for(
            "static",
            filename=(
                "uploads/community/"
                + stored_name
            )
        )

        if extension in IMAGE_EXTENSIONS:
            message_type = "image"
        else:
            message_type = "file"

        message = CommunityMessage(
            community_id=community_id,
            sender_id=current_user_id,
            message_type=message_type,
            content=None,
            file_url=file_url,
            file_name=original_name
        )

        db.session.add(
            message
        )

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        if os.path.exists(
            file_path
        ):
            try:
                os.remove(
                    file_path
                )
            except OSError:
                pass

        return jsonify({
            "success": False,
            "message":
                f"附件上傳失敗：{error}"
        }), 500

    return jsonify({
        "success": True,
        "message": "附件已傳送"
    })


# =========================================================
# 收回自己的訊息
# =========================================================

@community_bp.route(
    "/<int:community_id>/messages/<int:message_id>",
    methods=["DELETE"]
)
@login_required
def delete_community_message(
    community_id,
    message_id
):

    current_user_id = (
        session.get("user_id")
    )

    message = (
        CommunityMessage.query
        .filter_by(
            id=message_id,
            community_id=community_id
        )
        .first_or_404()
    )

    # 只能收回自己的訊息
    if (
        message.sender_id !=
        current_user_id
    ):

        return jsonify({
            "success": False,
            "message":
                "只能收回自己的訊息"
        }), 403

    file_path = None

    if message.file_url:

        file_name = os.path.basename(
            message.file_url
        )

        upload_folder = (
            current_app.config.get(
                "COMMUNITY_UPLOAD_FOLDER"
            )
        )

        if not upload_folder:

            upload_folder = os.path.join(
                current_app.static_folder,
                "uploads",
                "community"
            )

        file_path = os.path.join(
            upload_folder,
            file_name
        )

    try:

        db.session.delete(
            message
        )

        db.session.commit()

        # DB 成功後再刪實體附件
        if (
            file_path
            and os.path.exists(
                file_path
            )
        ):
            try:
                os.remove(
                    file_path
                )
            except OSError:
                pass

    except Exception as error:

        db.session.rollback()

        return jsonify({
            "success": False,
            "message":
                f"收回失敗：{error}"
        }), 500

    return jsonify({
        "success": True,
        "message": "訊息已收回"
    })


# =========================================================
# 建立者查看待審核申請
# =========================================================

@community_bp.route(
    "/<int:community_id>/join-requests",
    methods=["GET"]
)
@login_required
def get_join_requests(
    community_id
):

    current_user_id = (
        session.get("user_id")
    )

    community = (
        Community.query
        .get_or_404(
            community_id
        )
    )

    if (
        community.creator_id !=
        current_user_id
    ):

        return jsonify({
            "success": False,
            "message":
                "只有建立者可以查看加入申請"
        }), 403

    requests = (
        CommunityJoinRequest.query
        .filter_by(
            community_id=community_id,
            status="pending"
        )
        .order_by(
            CommunityJoinRequest
            .created_at
            .asc()
        )
        .all()
    )

    data = []

    for join_request in requests:

        user = join_request.user

        data.append({
            "id":
                join_request.id,

            "user_id":
                join_request.user_id,

            "user_name": (
                user.full_name
                if user
                else "未知使用者"
            ),

            "student_no": (
                getattr(
                    user,
                    "student_no",
                    None
                )
                if user
                else None
            ),

            "created_at": (
                join_request
                .created_at
                .strftime(
                    "%Y-%m-%d %H:%M"
                )
                if join_request.created_at
                else "-"
            )
        })

    return jsonify({
        "success": True,
        "data": data
    })


# =========================================================
# 同意加入
# =========================================================

@community_bp.route(
    "/<int:community_id>/join-requests/"
    "<int:request_id>/approve",
    methods=["POST"]
)
@login_required
def approve_join_request(
    community_id,
    request_id
):

    current_user_id = (
        session.get("user_id")
    )

    community = (
        Community.query
        .get_or_404(
            community_id
        )
    )

    if (
        community.creator_id !=
        current_user_id
    ):

        return jsonify({
            "success": False,
            "message":
                "只有建立者可以審核"
        }), 403

    join_request = (
        CommunityJoinRequest.query
        .filter_by(
            id=request_id,
            community_id=community_id
        )
        .first_or_404()
    )

    if (
        join_request.status !=
        "pending"
    ):

        return jsonify({
            "success": False,
            "message":
                "此申請已經處理"
        }), 400

    membership = (
        CommunityMember.query
        .filter_by(
            community_id=community_id,
            user_id=join_request.user_id
        )
        .first()
    )

    try:

        if not membership:

            membership = CommunityMember(
                community_id=community_id,
                user_id=join_request.user_id,
                role="member"
            )

            db.session.add(
                membership
            )

        join_request.status = (
            "accepted"
        )

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        return jsonify({
            "success": False,
            "message":
                f"審核失敗：{error}"
        }), 500

    return jsonify({
        "success": True,
        "message":
            "已同意加入申請"
    })


# =========================================================
# 拒絕加入
# =========================================================

@community_bp.route(
    "/<int:community_id>/join-requests/"
    "<int:request_id>/reject",
    methods=["POST"]
)
@login_required
def reject_join_request(
    community_id,
    request_id
):

    current_user_id = (
        session.get("user_id")
    )

    community = (
        Community.query
        .get_or_404(
            community_id
        )
    )

    if (
        community.creator_id !=
        current_user_id
    ):

        return jsonify({
            "success": False,
            "message":
                "只有建立者可以審核"
        }), 403

    join_request = (
        CommunityJoinRequest.query
        .filter_by(
            id=request_id,
            community_id=community_id
        )
        .first_or_404()
    )

    if (
        join_request.status !=
        "pending"
    ):

        return jsonify({
            "success": False,
            "message":
                "此申請已經處理"
        }), 400

    try:

        join_request.status = (
            "rejected"
        )

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        return jsonify({
            "success": False,
            "message":
                f"審核失敗：{error}"
        }), 500

    return jsonify({
        "success": True,
        "message":
            "已拒絕加入申請"
    })

# =========================================================
# 下載聊天室附件
# =========================================================

@community_bp.route(
    "/<int:community_id>/messages/<int:message_id>/download",
    methods=["GET"]
)
@login_required
def download_community_file(
    community_id,
    message_id
):
    current_user_id = session.get("user_id")

    community = Community.query.get_or_404(
        community_id
    )

    # 只有社團成員才能下載
    if not is_community_member(
        community,
        current_user_id
    ):
        return jsonify({
            "success": False,
            "message": "你不是此社群成員"
        }), 403

    message = (
        CommunityMessage.query
        .filter_by(
            id=message_id,
            community_id=community_id
        )
        .first_or_404()
    )

    if not message.file_url:
        return jsonify({
            "success": False,
            "message": "這則訊息沒有附件"
        }), 404

    stored_name = os.path.basename(
        message.file_url
    )

    upload_folder = (
        current_app.config.get(
            "COMMUNITY_UPLOAD_FOLDER"
        )
    )

    if not upload_folder:
        upload_folder = os.path.join(
            current_app.static_folder,
            "uploads",
            "community"
        )

    file_path = os.path.join(
        upload_folder,
        stored_name
    )

    if not os.path.exists(file_path):
        return jsonify({
            "success": False,
            "message": "附件檔案不存在"
        }), 404

    return send_from_directory(
        upload_folder,
        stored_name,
        as_attachment=True,
        download_name=(
            message.file_name
            or stored_name
        )
    )