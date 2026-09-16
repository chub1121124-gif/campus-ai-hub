let allNotes = [];
    let selectedNoteId = null;

    const noteList = document.getElementById("noteList");
    const noteTitle = document.getElementById("noteTitle");
    const noteCategory = document.getElementById("noteCategory");
    const noteContent = document.getElementById("noteContent");

    const searchInput = document.getElementById("searchInput");
    const searchCategory = document.getElementById("searchCategory");

    const editorTitle = document.getElementById("editorTitle");

    const deleteNoteButton =
        document.getElementById("deleteNoteButton");

    const attachmentSection =
        document.getElementById("attachmentSection");

    const attachmentList =
        document.getElementById("attachmentList");

    const attachmentFile =
        document.getElementById("attachmentFile");

    const noteInfoBar =
        document.getElementById("noteInfoBar");

    const noteIdText =
        document.getElementById("noteIdText");

    const createdAtText =
        document.getElementById("createdAtText");

    const updatedAtText =
        document.getElementById("updatedAtText");

    const progressArea =
        document.getElementById("progressArea");

    const progressBar =
        document.getElementById("progressBar");

    const progressText =
        document.getElementById("progressText");


    function escapeHTML(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }


    function showMessage(message, success = true) {
        const box =
            document.getElementById("messageBox");

        box.textContent = message;

        box.className = success
            ? "message-box message-success"
            : "message-box message-error";

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });

        setTimeout(() => {
            box.className = "message-box";
        }, 4000);
    }


    function formatFileSize(bytes) {
        const value = Number(bytes || 0);

        if (value < 1024) {
            return `${value} B`;
        }

        if (value < 1024 * 1024) {
            return `${(value / 1024).toFixed(1)} KB`;
        }

        if (value < 1024 * 1024 * 1024) {
            return `${(
                value /
                1024 /
                1024
            ).toFixed(1)} MB`;
        }

        return `${(
            value /
            1024 /
            1024 /
            1024
        ).toFixed(1)} GB`;
    }


    function getFileTypeName(type, fileName = "") {
        if (
            String(fileName)
                .toLowerCase()
                .endsWith(".pdf")
        ) {
            return "PDF 文件";
        }

        switch (type) {
            case "image":
                return "圖片";

            case "video":
                return "影片";

            case "audio":
                return "音訊檔案";

            case "archive":
                return "壓縮檔";

            case "code":
                return "程式碼";

            case "document":
                return "文件";

            default:
                return "附件";
        }
    }


    function getFileIcon(type, fileName = "") {
        if (
            String(fileName)
                .toLowerCase()
                .endsWith(".pdf")
        ) {
            return "📕";
        }

        switch (type) {
            case "image":
                return "🖼️";

            case "video":
                return "🎬";

            case "audio":
                return "🎵";

            case "archive":
                return "🗜️";

            case "code":
                return "💻";

            default:
                return "📄";
        }
    }


    async function loadNotes() {
        try {
            const keyword =
                searchInput.value.trim();

            const category =
                searchCategory.value;

            const params =
                new URLSearchParams();

            if (keyword) {
                params.set("q", keyword);
            }

            if (category) {
                params.set(
                    "category",
                    category
                );
            }

            const url =
                params.toString()
                    ? `/api/notes?${params.toString()}`
                    : "/api/notes";

            const response =
                await fetch(url);

            const result =
                await response.json();

            if (
                !response.ok ||
                !result.success
            ) {
                throw new Error(
                    result.message ||
                    "載入筆記失敗"
                );
            }

            allNotes =
                result.data || [];

            renderNoteList();

        } catch (error) {

            noteList.innerHTML = `
                <div class="empty-state">
                    ${escapeHTML(error.message)}
                </div>
            `;
        }
    }


    function renderNoteList() {
        noteList.innerHTML = "";

        if (!allNotes.length) {
            noteList.innerHTML = `
                <div class="empty-state">
                    目前沒有符合條件的筆記。<br><br>
                    點上方「＋新增」建立第一篇筆記。
                </div>
            `;
            return;
        }

        allNotes.forEach(note => {

            const button =
                document.createElement("button");

            button.type = "button";

            button.className =
                "note-list-item";

            if (
                Number(note.id) ===
                Number(selectedNoteId)
            ) {
                button.classList.add(
                    "active"
                );
            }

            button.innerHTML = `
                <div class="note-list-title">
                    ${escapeHTML(note.title)}
                </div>

                <span class="note-list-category">
                    ${escapeHTML(
                note.category ||
                "一般筆記"
            )}
                </span>

                <div class="note-list-preview">
                    ${escapeHTML(
                note.content ||
                "尚無內容"
            )}
                </div>

                <div class="note-list-time">
                    最後修改：
                    ${escapeHTML(
                note.updated_at ||
                "尚無資料"
            )}
                </div>
            `;

            button.addEventListener(
                "click",
                () => {
                    selectNote(note.id);
                }
            );

            noteList.appendChild(
                button
            );
        });
    }


    function newNote() {
        selectedNoteId = null;

        editorTitle.textContent =
            "新增筆記";

        noteTitle.value = "";
        noteCategory.value =
            "一般筆記";
        noteContent.value = "";

        deleteNoteButton.style.display =
            "none";

        attachmentSection.style.display =
            "none";

        noteInfoBar.style.display =
            "none";

        attachmentList.innerHTML = "";

        renderNoteList();

        noteTitle.focus();
    }


    function selectNote(noteId) {
        const note =
            allNotes.find(
                item =>
                    Number(item.id) ===
                    Number(noteId)
            );

        if (!note) {
            return;
        }

        selectedNoteId =
            note.id;

        editorTitle.textContent =
            "修改筆記";

        noteTitle.value =
            note.title || "";

        noteCategory.value =
            note.category ||
            "一般筆記";

        noteContent.value =
            note.content || "";

        deleteNoteButton.style.display =
            "inline-flex";

        attachmentSection.style.display =
            "block";

        noteInfoBar.style.display =
            "flex";

        noteIdText.textContent =
            `筆記編號：${note.id}`;

        createdAtText.textContent =
            `建立時間：${note.created_at || "-"
            }`;

        updatedAtText.textContent =
            `最後修改：${note.updated_at || "-"
            }`;

        renderAttachments(
            note.attachments || []
        );

        renderNoteList();
    }


    async function saveCurrentNote() {

        const title =
            noteTitle.value.trim();

        const content =
            noteContent.value.trim();

        const category =
            noteCategory.value;

        if (!title) {
            showMessage(
                "請輸入筆記標題",
                false
            );
            noteTitle.focus();
            return;
        }

        if (!content) {
            showMessage(
                "請輸入筆記內容",
                false
            );
            noteContent.focus();
            return;
        }

        try {
            let response;

            if (!selectedNoteId) {

                response =
                    await fetch(
                        "/api/notes",
                        {
                            method: "POST",
                            headers: {
                                "Content-Type":
                                    "application/json"
                            },
                            body: JSON.stringify({
                                title,
                                content,
                                category
                            })
                        }
                    );

            } else {

                response =
                    await fetch(
                        `/api/notes/${selectedNoteId}`,
                        {
                            method: "PUT",
                            headers: {
                                "Content-Type":
                                    "application/json"
                            },
                            body: JSON.stringify({
                                title,
                                content,
                                category
                            })
                        }
                    );
            }

            const result =
                await response.json();

            if (
                !response.ok ||
                !result.success
            ) {
                throw new Error(
                    result.message ||
                    "儲存失敗"
                );
            }

            showMessage(
                result.message ||
                "筆記已儲存"
            );

            selectedNoteId =
                result.data.id;

            await loadNotes();

            selectNote(
                selectedNoteId
            );

        } catch (error) {

            showMessage(
                error.message,
                false
            );
        }
    }


    async function deleteCurrentNote() {

        if (!selectedNoteId) {
            return;
        }

        const confirmed =
            confirm(
                "確定要刪除此筆記嗎？\n\n" +
                "筆記內的附件也會一起刪除，" +
                "而且無法復原。"
            );

        if (!confirmed) {
            return;
        }

        try {

            const response =
                await fetch(
                    `/api/notes/${selectedNoteId}`,
                    {
                        method: "DELETE"
                    }
                );

            const result =
                await response.json();

            if (
                !response.ok ||
                !result.success
            ) {
                throw new Error(
                    result.message ||
                    "刪除失敗"
                );
            }

            showMessage(
                result.message ||
                "筆記已刪除"
            );

            selectedNoteId = null;

            newNote();

            await loadNotes();

        } catch (error) {

            showMessage(
                error.message,
                false
            );
        }
    }


    function renderAttachments(
        attachments
    ) {
        attachmentList.innerHTML = "";

        if (!attachments.length) {

            attachmentList.innerHTML = `
                <div class="empty-state">
                    此筆記目前沒有附件。<br>
                    可在上方選擇文件、圖片、
                    影片或音檔上傳。
                </div>
            `;

            return;
        }

        attachments.forEach(
            attachment => {

                const card =
                    document.createElement(
                        "div"
                    );

                card.className =
                    "attachment-card";

                const type =
                    attachment
                        .attachment_type ||
                    "document";

                const fileName =
                    attachment
                        .original_name ||
                    "未命名附件";

                const url =
                    attachment.file_url;

                let previewHTML = "";

                if (
                    type === "image"
                ) {

                    previewHTML = `
                        <img
                            class="
                                attachment-preview
                                attachment-image
                            "
                            src="${escapeHTML(url)
                        }"
                            alt="${escapeHTML(
                            fileName
                        )
                        }"
                        >
                    `;

                } else if (
                    type === "video"
                ) {

                    previewHTML = `
                        <video
                            class="
                                attachment-preview
                                attachment-video
                            "
                            src="${escapeHTML(url)
                        }"
                            controls
                            preload="metadata"
                        ></video>
                    `;

                } else if (
                    type === "audio"
                ) {

                    previewHTML = `
                        <div class="file-icon-box">
                            🎵
                        </div>

                        <audio
                            class="attachment-audio"
                            controls
                            preload="metadata"
                            src="${escapeHTML(url)
                        }"
                        ></audio>
                    `;

                } else if (
                    fileName
                        .toLowerCase()
                        .endsWith(".pdf")
                ) {

                    previewHTML = `
                        <iframe
                            class="
                                attachment-preview
                                attachment-pdf
                            "
                            src="${escapeHTML(url)
                        }"
                        ></iframe>
                    `;

                } else {

                    previewHTML = `
                        <div class="file-icon-box">
                            ${getFileIcon(
                        type,
                        fileName
                    )
                        }
                        </div>
                    `;
                }

                card.innerHTML = `
                    ${previewHTML}

                    <span
                        class="
                            attachment-type-label
                        "
                    >
                        ${escapeHTML(
                    getFileTypeName(
                        type,
                        fileName
                    )
                )
                    }
                    </span>

                    <div class="attachment-name">
                        ${escapeHTML(
                        fileName
                    )
                    }
                    </div>

                    <div class="attachment-meta">
                        檔案大小：
                        ${formatFileSize(
                        attachment
                            .file_size
                    )
                    }
                        <br>

                        上傳時間：
                        ${escapeHTML(
                        attachment
                            .uploaded_at ||
                        "-"
                    )
                    }
                    </div>

                    <div
                        class="
                            attachment-actions
                        "
                    >
                        <a
                            class="
                                btn
                                btn-secondary
                            "
                            href="${escapeHTML(url)
                    }"
                            target="_blank"
                            rel="noopener"
                        >
                            開啟
                        </a>

                        <a
                            class="
                                btn
                                btn-primary
                            "
                            href="${escapeHTML(url)
                    }"
                            download
                        >
                            下載
                        </a>

                        <button
                            type="button"
                            class="
                                btn
                                btn-danger
                            "
                            onclick="
                                deleteAttachment(
                                    ${attachment.id}
                                )
                            "
                        >
                            刪除
                        </button>
                    </div>
                `;

                attachmentList.appendChild(
                    card
                );
            }
        );
    }


    function uploadAttachment() {

        if (!selectedNoteId) {
            showMessage(
                "請先建立或選擇一篇筆記",
                false
            );
            return;
        }

        const file =
            attachmentFile.files[0];

        if (!file) {
            showMessage(
                "請先選擇檔案",
                false
            );
            return;
        }

        const formData =
            new FormData();

        formData.append(
            "file",
            file
        );

        const xhr =
            new XMLHttpRequest();

        xhr.open(
            "POST",
            `/api/notes/${selectedNoteId}/attachments`
        );

        progressArea.style.display =
            "block";

        progressBar.style.width =
            "0%";

        progressText.textContent =
            "準備上傳...";

        xhr.upload.addEventListener(
            "progress",
            event => {

                if (
                    !event.lengthComputable
                ) {
                    return;
                }

                const percentage =
                    Math.round(
                        event.loaded /
                        event.total *
                        100
                    );

                progressBar.style.width =
                    `${percentage}%`;

                progressText.textContent =
                    `上傳中 ${percentage}%`;
            }
        );

        xhr.addEventListener(
            "load",
            async () => {

                let result;

                try {
                    result =
                        JSON.parse(
                            xhr.responseText
                        );
                } catch {
                    result = {
                        success: false,
                        message:
                            "伺服器回傳格式錯誤"
                    };
                }

                if (
                    xhr.status >= 200 &&
                    xhr.status < 300 &&
                    result.success
                ) {

                    progressBar.style.width =
                        "100%";

                    progressText.textContent =
                        "上傳完成";

                    attachmentFile.value =
                        "";

                    showMessage(
                        result.message ||
                        "附件上傳成功"
                    );

                    await reloadSelectedNote();

                } else {

                    progressText.textContent =
                        "上傳失敗";

                    showMessage(
                        result.message ||
                        "附件上傳失敗",
                        false
                    );
                }
            }
        );

        xhr.addEventListener(
            "error",
            () => {

                progressText.textContent =
                    "網路錯誤";

                showMessage(
                    "附件上傳失敗",
                    false
                );
            }
        );

        xhr.send(formData);
    }


    async function deleteAttachment(
        attachmentId
    ) {

        const confirmed =
            confirm(
                "確定要刪除此附件嗎？"
            );

        if (!confirmed) {
            return;
        }

        try {

            const response =
                await fetch(
                    `/api/notes/attachments/${attachmentId}`,
                    {
                        method: "DELETE"
                    }
                );

            const result =
                await response.json();

            if (
                !response.ok ||
                !result.success
            ) {
                throw new Error(
                    result.message ||
                    "刪除附件失敗"
                );
            }

            showMessage(
                result.message ||
                "附件已刪除"
            );

            await reloadSelectedNote();

        } catch (error) {

            showMessage(
                error.message,
                false
            );
        }
    }


    async function reloadSelectedNote() {

        if (!selectedNoteId) {
            return;
        }

        try {

            const response =
                await fetch(
                    `/api/notes/${selectedNoteId}`
                );

            const result =
                await response.json();

            if (
                !response.ok ||
                !result.success
            ) {
                throw new Error(
                    result.message ||
                    "更新筆記資料失敗"
                );
            }

            const updatedNote =
                result.data;

            const index =
                allNotes.findIndex(
                    note =>
                        Number(note.id) ===
                        Number(
                            selectedNoteId
                        )
                );

            if (index !== -1) {
                allNotes[index] =
                    updatedNote;
            }

            selectNote(
                selectedNoteId
            );

        } catch (error) {

            showMessage(
                error.message,
                false
            );
        }
    }


    let searchTimer = null;

    searchInput.addEventListener(
        "input",
        () => {

            clearTimeout(
                searchTimer
            );

            searchTimer =
                setTimeout(
                    loadNotes,
                    300
                );
        }
    );


    searchCategory.addEventListener(
        "change",
        loadNotes
    );


    document
        .querySelectorAll(
            ".category-btn"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                () => {

                    document
                        .querySelectorAll(
                            ".category-btn"
                        )
                        .forEach(item => {
                            item.classList
                                .remove(
                                    "active"
                                );
                        });

                    button.classList.add(
                        "active"
                    );

                    searchCategory.value =
                        button.dataset
                            .category || "";

                    loadNotes();
                }
            );
        });


    loadNotes();
    newNote();
