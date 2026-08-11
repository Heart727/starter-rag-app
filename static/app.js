/* ==========================================
   知识库问答 - 前端逻辑
   ========================================== */

// ===== DOM 元素 =====
var fileInput = document.getElementById('fileInput');
var selectBtn = document.getElementById('selectBtn');
var fileList = document.getElementById('fileList');
var uploadBtn = document.getElementById('uploadBtn');
var processBtn = document.getElementById('processBtn');
var statusBar = document.getElementById('statusBar');
var statusIcon = document.getElementById('statusIcon');
var statusText = document.getElementById('statusText');
var questionInput = document.getElementById('questionInput');
var askBtn = document.getElementById('askBtn');
var chatBox = document.getElementById('chatBox');
var chatEmpty = document.querySelector('.chat-empty');

var selectedFiles = [];

// ===== 文件选择 =====
selectBtn.addEventListener('click', function () {
    fileInput.click();
});

fileInput.addEventListener('change', function () {
    selectedFiles = Array.from(fileInput.files);
    if (selectedFiles.length === 0) {
        fileList.textContent = '未选择文件';
        uploadBtn.disabled = true;
        return;
    }
    fileList.textContent = '已选择 ' + selectedFiles.length + ' 个文件：' + selectedFiles.map(function (f) { return f.name; }).join('，');
    uploadBtn.disabled = false;
});

// ===== 上传文件 =====
uploadBtn.addEventListener('click', function () {
    var formData = new FormData();
    selectedFiles.forEach(function (file) {
        formData.append('files', file);
    });

    showStatus('processing', '⏳ 正在上传...');
    uploadBtn.disabled = true;

    fetch('/api/upload', { method: 'POST', body: formData })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            showStatus('success', '✅ ' + data.message);
            processBtn.disabled = false;
        })
        .catch(function (err) {
            showStatus('error', '❌ 上传失败: ' + err.message);
            uploadBtn.disabled = false;
        });
});

// ===== 处理文档 =====
processBtn.addEventListener('click', function () {
    showStatus('processing', '⏳ 正在处理文档（读取 → 切片 → 向量化）...');
    processBtn.disabled = true;

    fetch('/api/process', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            showStatus('success', '✅ ' + data.message);
            // 启用问答
            questionInput.disabled = false;
            askBtn.disabled = false;
            hideChatEmpty();
        })
        .catch(function (err) {
            showStatus('error', '❌ 处理失败: ' + err.message);
            processBtn.disabled = false;
        });
});

// ===== 提问 =====
askBtn.addEventListener('click', function () {
    askQuestion();
});

questionInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') askQuestion();
});

function askQuestion() {
    var question = questionInput.value.trim();
    if (!question) return;

    hideChatEmpty();
    addMessage('question', question);
    questionInput.value = '';

    var loadingMsg = addMessage('answer', '⏳ 正在检索和生成答案...');

    fetch('/api/query?question=' + encodeURIComponent(question))
        .then(function (r) { return r.json(); })
        .then(function (data) {
            loadingMsg.remove();
            if (data.error) {
                addMessage('error', '❌ ' + data.error);
            } else {
                addMessage('answer', data.answer, data.sources);
            }
        })
        .catch(function (err) {
            loadingMsg.remove();
            addMessage('error', '❌ 请求失败: ' + err.message);
        });
}

// ===== 辅助函数 =====
function showStatus(type, msg) {
    statusBar.classList.remove('hidden', 'success', 'error', 'processing');
    statusBar.classList.add(type);
    statusText.textContent = msg;
}

function hideChatEmpty() {
    if (chatEmpty) {
        chatEmpty.style.display = 'none';
    }
}

function addMessage(type, text, sources) {
    hideChatEmpty();
    var div = document.createElement('div');
    div.className = 'msg ' + type;

    // XSS 防护：用 textContent 而非 innerHTML
    var contentSpan = document.createElement('span');
    contentSpan.textContent = text;
    div.appendChild(contentSpan);

    // 来源信息
    if (sources && sources.length > 0) {
        var details = document.createElement('details');
        details.className = 'sources';
        var summary = document.createElement('summary');
        summary.textContent = '📎 查看检索来源（' + sources.length + ' 条）';
        details.appendChild(summary);

        sources.forEach(function (src, i) {
            var p = document.createElement('p');
            p.textContent = '片段 ' + (i + 1) + '（相关度: ' + src.score + '）: ' + src.text;
            details.appendChild(p);
        });
        div.appendChild(details);
    }

    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
    return div;
}
