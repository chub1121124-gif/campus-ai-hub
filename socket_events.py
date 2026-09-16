from datetime import datetime

from flask import (
    request,
    session
)

from flask_socketio import (
    emit,
    join_room,
    leave_room
)

from extensions import (
    db,
    socketio
)

from models import (
    Meeting,
    MeetingParticipant,
    User
)


# ============================================================
# Socket SID → 使用者目前所在會議
# ============================================================

socket_meetings = {}


def meeting_room_name(
    meeting_id
):
    return (
        f"meeting-{meeting_id}"
    )


def get_user():
    user_id = session.get(
        "user_id"
    )

    if not user_id:
        return None

    return db.session.get(
        User,
        user_id
    )


# ============================================================
# 加入會議
# ============================================================

@socketio.on("join_meeting")
def handle_join_meeting(data):

    current_user = get_user()

    if not current_user:

        emit(
            "meeting_error",
            {
                "message":
                    "請先登入"
            }
        )

        return

    try:

        meeting_id = int(
            data.get(
                "meeting_id"
            )
        )

    except (
        TypeError,
        ValueError
    ):

        emit(
            "meeting_error",
            {
                "message":
                    "會議編號錯誤"
            }
        )

        return

    meeting = db.session.get(
        Meeting,
        meeting_id
    )

    if not meeting:

        emit(
            "meeting_closed",
            {
                "message":
                    "找不到此會議"
            }
        )

        return

    if meeting.status == "ended":

        emit(
            "meeting_closed",
            {
                "message":
                    "此會議已結束"
            }
        )

        return

    room = meeting_room_name(
        meeting_id
    )

    # 先取得已經在線上的人
    existing_participants = (
        MeetingParticipant.query
        .filter_by(
            meeting_id=meeting_id,
            left_at=None
        )
        .all()
    )

    existing_users = []

    for participant in (
        existing_participants
    ):

        if (
            participant.user_id
            == current_user.id
        ):
            continue

        existing_users.append({
            "user_id":
                participant.user_id,

            "full_name": (
                participant.user.full_name
                if participant.user
                else "未知"
            ),

            "avatar_url": (
                participant.user.avatar_url
                if participant.user
                else None
            )
        })

    # 加入 Socket 房間
    join_room(room)

    socket_meetings[
        request.sid
    ] = {
        "meeting_id":
            meeting_id,

        "user_id":
            current_user.id
    }

    # 使用者重新加入時
    # 關閉舊紀錄
    old_active = (
        MeetingParticipant.query
        .filter_by(
            meeting_id=meeting_id,
            user_id=current_user.id,
            left_at=None
        )
        .all()
    )

    for old_item in old_active:
        old_item.left_at = (
            datetime.utcnow()
        )

    participant = (
        MeetingParticipant(
            meeting_id=meeting_id,
            user_id=current_user.id,
            joined_at=datetime.utcnow(),
            left_at=None
        )
    )

    db.session.add(participant)

    meeting.status = "active"

    db.session.commit()

    # 告訴本人目前有哪些人
    emit(
        "meeting_joined",
        {
            "meeting_id":
                meeting_id,

            "current_user": {
                "id":
                    current_user.id,

                "full_name":
                    current_user.full_name
            },

            "participants":
                existing_users
        }
    )

    # 告訴其他人有人進來
    emit(
        "participant_joined",
        {
            "user_id":
                current_user.id,

            "full_name":
                current_user.full_name,

            "avatar_url":
                current_user.avatar_url,

            "socket_id":
                request.sid
        },
        to=room,
        include_self=False
    )


# ============================================================
# WebRTC Offer
# ============================================================

@socketio.on("webrtc_offer")
def handle_webrtc_offer(data):

    target_sid = data.get(
        "target_sid"
    )

    if not target_sid:
        return

    emit(
        "webrtc_offer",
        {
            "offer":
                data.get("offer"),

            "sender_sid":
                request.sid,

            "sender_user_id":
                session.get("user_id")
        },
        to=target_sid
    )


# ============================================================
# WebRTC Answer
# ============================================================

@socketio.on("webrtc_answer")
def handle_webrtc_answer(data):

    target_sid = data.get(
        "target_sid"
    )

    if not target_sid:
        return

    emit(
        "webrtc_answer",
        {
            "answer":
                data.get("answer"),

            "sender_sid":
                request.sid
        },
        to=target_sid
    )


# ============================================================
# ICE Candidate
# ============================================================

@socketio.on(
    "webrtc_ice_candidate"
)
def handle_ice_candidate(data):

    target_sid = data.get(
        "target_sid"
    )

    if not target_sid:
        return

    emit(
        "webrtc_ice_candidate",
        {
            "candidate":
                data.get(
                    "candidate"
                ),

            "sender_sid":
                request.sid
        },
        to=target_sid
    )


# ============================================================
# 離開會議
# ============================================================

@socketio.on("leave_meeting")
def handle_leave_meeting(data):

    current_user = get_user()

    if not current_user:
        return

    try:

        meeting_id = int(
            data.get(
                "meeting_id"
            )
        )

    except (
        TypeError,
        ValueError
    ):
        return

    close_for_all = bool(
        data.get(
            "close_for_all",
            False
        )
    )

    leave_meeting_internal(
        meeting_id=meeting_id,
        user_id=current_user.id,
        close_for_all=close_for_all,
        sid=request.sid
    )


# ============================================================
# 真正處理離開
# ============================================================

def leave_meeting_internal(
    meeting_id,
    user_id,
    close_for_all=False,
    sid=None
):

    meeting = db.session.get(
        Meeting,
        meeting_id
    )

    if not meeting:
        return

    room = meeting_room_name(
        meeting_id
    )

    # --------------------------------------------------------
    # 建立者選擇「結束所有人的會議」
    # --------------------------------------------------------

    if (
        meeting.created_by
        == user_id
        and close_for_all
    ):

        emit(
            "meeting_closed",
            {
                "message":
                    "會議建立者已結束會議"
            },
            to=room
        )

        MeetingParticipant.query.filter_by(
            meeting_id=meeting_id
        ).delete(
            synchronize_session=False
        )

        db.session.delete(
            meeting
        )

        db.session.commit()

        if sid:
            socket_meetings.pop(
                sid,
                None
            )

        return

    # --------------------------------------------------------
    # 只退出自己
    # --------------------------------------------------------

    participant = (
        MeetingParticipant.query
        .filter_by(
            meeting_id=meeting_id,
            user_id=user_id,
            left_at=None
        )
        .order_by(
            MeetingParticipant
            .joined_at.desc()
        )
        .first()
    )

    if participant:

        participant.left_at = (
            datetime.utcnow()
        )

        db.session.commit()

    if sid:

        try:
            leave_room(
                room,
                sid=sid
            )
        except Exception:
            pass

        socket_meetings.pop(
            sid,
            None
        )

    emit(
        "participant_left",
        {
            "user_id":
                user_id,

            "socket_id":
                sid
        },
        to=room
    )

    # --------------------------------------------------------
    # 最後一個人退出 → 直接刪除整個會議
    # --------------------------------------------------------

    active_count = (
        MeetingParticipant.query
        .filter_by(
            meeting_id=meeting_id,
            left_at=None
        )
        .count()
    )

    if active_count == 0:

        MeetingParticipant.query.filter_by(
            meeting_id=meeting_id
        ).delete(
            synchronize_session=False
        )

        db.session.delete(
            meeting
        )

        db.session.commit()


# ============================================================
# Socket 意外斷線
# ============================================================

@socketio.on("disconnect")
def handle_disconnect():

    info = socket_meetings.pop(
        request.sid,
        None
    )

    if not info:
        return

    meeting_id = info.get(
        "meeting_id"
    )

    user_id = info.get(
        "user_id"
    )

    if (
        not meeting_id
        or not user_id
    ):
        return

    # 關掉分頁、斷網等情況
    # 一律視為只退出自己
    leave_meeting_internal(
        meeting_id=meeting_id,
        user_id=user_id,
        close_for_all=False,
        sid=request.sid
    )