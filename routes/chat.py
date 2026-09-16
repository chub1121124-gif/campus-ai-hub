import os
import time
from flask import Blueprint, jsonify, request, session, current_app
from werkzeug.utils import secure_filename
from extensions import db
from models import (
    User,
    Friendship,
    ChatRoom,
    ChatRoomMember,
    ChatJoinRequest,
    ChatMessage
)
from .auth import login_required
from services.chat_service import (
    get_accepted_friends,
    get_or_create_private_room,
    user_in_room,
)
from utils.auth_helpers import get_logged_in_user

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")




@chat_bp.route("/search-users")
@login_required
def search_users():
    q = request.args.get("q", "").strip()
    current_user = get_logged_in_user()

    if not q:
        return jsonify({"success": True, "data": []})

    users = User.query.filter(
        User.id != current_user.id,
        db.or_(
            User.full_name.contains(q),
            User.student_no.contains(q),
            User.username.contains(q)
        )
    ).all()

    return jsonify({
        "success": True,
        "data": [u.to_dict() for u in users]
    })


@chat_bp.route("/friends/request", methods=["POST"])
@login_required
def send_friend_request():
    current_user = get_logged_in_user()
    data = request.get_json()
    target_user_id = data.get("target_user_id")

    if not target_user_id:
        return jsonify({"success": False, "message": "缺少目標使用者"}), 400

    if int(target_user_id) == current_user.id:
        return jsonify({"success": False, "message": "不能加自己為好友"}), 400

    target_user = User.query.get(target_user_id)
    if not target_user:
        return jsonify({"success": False, "message": "找不到使用者"}), 404

    existing = Friendship.query.filter(
        db.or_(
            db.and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == target_user.id),
            db.and_(Friendship.requester_id == target_user.id, Friendship.addressee_id == current_user.id)
        )
    ).first()

    if existing:
        return jsonify({"success": False, "message": "好友邀請已存在或已是好友"}), 400

    friendship = Friendship(
        requester_id=current_user.id,
        addressee_id=target_user.id,
        status="pending"
    )
    db.session.add(friendship)
    db.session.commit()

    return jsonify({"success": True, "message": "好友邀請已送出"})


@chat_bp.route("/friends")
@login_required
def get_friends():
    current_user = get_logged_in_user()

    return jsonify({
        "success": True,
        "data": get_accepted_friends(current_user.id)
    })


@chat_bp.route("/friends/requests")
@login_required
def get_friend_requests():
    current_user = get_logged_in_user()
    requests = Friendship.query.filter_by(addressee_id=current_user.id, status="pending").all()
    return jsonify({
        "success": True,
        "data": [r.to_dict() for r in requests]
    })


@chat_bp.route("/friends/respond/<int:request_id>", methods=["POST"])
@login_required
def respond_friend_request(request_id):
    current_user = get_logged_in_user()
    data = request.get_json()
    action = data.get("action")

    friend_request = Friendship.query.get(request_id)
    if not friend_request:
        return jsonify({"success": False, "message": "找不到好友邀請"}), 404

    if friend_request.addressee_id != current_user.id:
        return jsonify({"success": False, "message": "無權操作"}), 403

    if action not in ["accept", "reject"]:
        return jsonify({"success": False, "message": "無效操作"}), 400

    if action == "accept":
        friend_request.status = "accepted"
        db.session.commit()
        room = get_or_create_private_room(friend_request.requester_id, friend_request.addressee_id)
        return jsonify({
            "success": True,
            "message": "已接受好友邀請",
            "data": {"private_room_id": room.id}
        })

    friend_request.status = "rejected"
    db.session.commit()
    return jsonify({"success": True, "message": "已拒絕好友邀請"})


@chat_bp.route("/rooms")
@login_required
def get_rooms():
    current_user = get_logged_in_user()
    memberships = ChatRoomMember.query.filter_by(user_id=current_user.id).all()
    room_ids = [m.room_id for m in memberships]
    rooms = ChatRoom.query.filter(ChatRoom.id.in_(room_ids)).order_by(ChatRoom.created_at.desc()).all() if room_ids else []

    return jsonify({
        "success": True,
        "data": [room.to_dict() for room in rooms]
    })


@chat_bp.route("/rooms/create", methods=["POST"])
@login_required
def create_room():
    current_user = get_logged_in_user()
    data = request.get_json()

    name = data.get("name", "").strip()
    topic = data.get("topic", "").strip()
    room_type = data.get("room_type", "group")
    require_approval = bool(data.get("require_approval", False))

    if not name:
        return jsonify({"success": False, "message": "聊天室名稱必填"}), 400

    room = ChatRoom(
        name=name,
        topic=topic,
        room_type=room_type,
        require_approval=require_approval,
        created_by=current_user.id
    )
    db.session.add(room)
    db.session.commit()

    owner_member = ChatRoomMember(
        room_id=room.id,
        user_id=current_user.id,
        role="owner"
    )
    db.session.add(owner_member)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "聊天室建立成功",
        "data": room.to_dict()
    })


@chat_bp.route("/rooms/<int:room_id>/join", methods=["POST"])
@login_required
def join_room(room_id):
    current_user = get_logged_in_user()
    room = ChatRoom.query.get(room_id)

    if not room:
        return jsonify({"success": False, "message": "找不到聊天室"}), 404

    if user_in_room(current_user.id, room.id):
        return jsonify({"success": False, "message": "你已經在此聊天室"}), 400

    if room.require_approval:
        existing_request = ChatJoinRequest.query.filter_by(
            room_id=room.id,
            user_id=current_user.id,
            status="pending"
        ).first()
        if existing_request:
            return jsonify({"success": False, "message": "已送出申請，請等待審核"}), 400

        join_request = ChatJoinRequest(
            room_id=room.id,
            user_id=current_user.id,
            status="pending"
        )
        db.session.add(join_request)
        db.session.commit()
        return jsonify({"success": True, "message": "已送出加入申請"})

    member = ChatRoomMember(room_id=room.id, user_id=current_user.id, role="member")
    db.session.add(member)
    db.session.commit()
    return jsonify({"success": True, "message": "已加入聊天室"})


@chat_bp.route("/rooms/<int:room_id>/requests")
@login_required
def get_join_requests(room_id):
    current_user = get_logged_in_user()
    room = ChatRoom.query.get(room_id)

    if not room:
        return jsonify({"success": False, "message": "找不到聊天室"}), 404

    owner_membership = ChatRoomMember.query.filter_by(room_id=room.id, user_id=current_user.id).first()
    if room.created_by != current_user.id and (not owner_membership or owner_membership.role not in ["owner", "admin"]):
        return jsonify({"success": False, "message": "無權查看申請"}), 403

    requests = ChatJoinRequest.query.filter_by(room_id=room.id, status="pending").all()
    return jsonify({
        "success": True,
        "data": [r.to_dict() for r in requests]
    })


@chat_bp.route("/rooms/<int:room_id>/requests/<int:request_id>/respond", methods=["POST"])
@login_required
def respond_join_request(room_id, request_id):
    current_user = get_logged_in_user()
    data = request.get_json()
    action = data.get("action")

    room = ChatRoom.query.get(room_id)
    if not room:
        return jsonify({"success": False, "message": "找不到聊天室"}), 404

    if room.created_by != current_user.id:
        return jsonify({"success": False, "message": "只有建立者可審核"}), 403

    join_request = ChatJoinRequest.query.get(request_id)
    if not join_request or join_request.room_id != room.id:
        return jsonify({"success": False, "message": "找不到申請"}), 404

    if action == "accept":
        join_request.status = "accepted"
        db.session.add(ChatRoomMember(room_id=room.id, user_id=join_request.user_id, role="member"))
        db.session.commit()
        return jsonify({"success": True, "message": "已同意加入"})

    join_request.status = "rejected"
    db.session.commit()
    return jsonify({"success": True, "message": "已拒絕加入"})


@chat_bp.route("/rooms/<int:room_id>/messages")
@login_required
def get_messages(room_id):
    current_user = get_logged_in_user()

    if not user_in_room(current_user.id, room_id):
        return jsonify({"success": False, "message": "你不是此聊天室成員"}), 403

    messages = ChatMessage.query.filter_by(room_id=room_id).order_by(ChatMessage.created_at.asc()).all()
    return jsonify({
        "success": True,
        "data": [m.to_dict() for m in messages]
    })


@chat_bp.route("/rooms/<int:room_id>/messages", methods=["POST"])
@login_required
def send_message(room_id):
    current_user = get_logged_in_user()

    if not user_in_room(current_user.id, room_id):
        return jsonify({"success": False, "message": "你不是此聊天室成員"}), 403

    content = request.form.get("content", "").strip()
    file = request.files.get("file")

    message_type = "text"
    file_url = None
    file_name = None

    if file and file.filename:
        filename = secure_filename(file.filename)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        new_filename = f"chat_{current_user.id}_{room_id}_{int(time.time())}.{ext}" if ext else f"chat_{current_user.id}_{room_id}"
        save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], new_filename)
        file.save(save_path)
        file_url = f"/static/uploads/{new_filename}"
        file_name = filename

        if ext in ["png", "jpg", "jpeg", "gif", "webp"]:
            message_type = "image"
        else:
            message_type = "file"

    if not content and not file_url:
        return jsonify({"success": False, "message": "訊息內容不可為空"}), 400

    message = ChatMessage(
        room_id=room_id,
        sender_id=current_user.id,
        message_type=message_type,
        content=content if content else None,
        file_url=file_url,
        file_name=file_name
    )
    db.session.add(message)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "訊息已送出",
        "data": message.to_dict()
    })


@chat_bp.route("/messages/<int:message_id>/edit", methods=["POST"])
@login_required
def edit_message(message_id):
    current_user = get_logged_in_user()
    message = ChatMessage.query.get(message_id)

    if not message:
        return jsonify({"success": False, "message": "找不到訊息"}), 404

    if message.sender_id != current_user.id:
        return jsonify({"success": False, "message": "只能修改自己的訊息"}), 403

    data = request.get_json()
    content = data.get("content", "").strip()

    if not content:
        return jsonify({"success": False, "message": "內容不可為空"}), 400

    message.content = content
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "訊息已修改",
        "data": message.to_dict()
    })


@chat_bp.route("/messages/<int:message_id>/delete", methods=["POST"])
@login_required
def delete_message(message_id):
    current_user = get_logged_in_user()
    message = ChatMessage.query.get(message_id)

    if not message:
        return jsonify({"success": False, "message": "找不到訊息"}), 404

    if message.sender_id != current_user.id and current_user.role != "admin":
        return jsonify({"success": False, "message": "無權刪除"}), 403

    db.session.delete(message)
    db.session.commit()
    return jsonify({"success": True, "message": "訊息已刪除"})