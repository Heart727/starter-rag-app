const fileInput = document.getElementById('fileInput');
const selectBtn = document.getElementById('selectBtn');
const fileList = document.getElementById('fileList');
const uploadBtn = document.getElementById('uploadBtn');
const processBtn = document.getElementById('processBtn');
const statusBar = document.getElementById('statusBar');
const statusText = document.getElementById('statusText');
const questionInput = document.getElementById('questionInput');
const askBtn = document.getElementById('askBtn');
const chatBox = document.getElementById('chatBox');
const chatEmpty = document.querySelector('.chat-empty');
const knowledgeStatus = document.getElementById('knowledgeStatus').parentElement;

const MAX_FILES = 5;
const MAX_FILE_BYTES = 10 * 1024 * 1024;
const MAX_TOTAL_BYTES = 20 * 1024 * 1024;
let selectedFiles = [];
let conversationHistory = [];

selectBtn.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', () => {
    selectedFiles = Array.from(fileInput.files);
    const totalBytes = selectedFiles.reduce((sum, file) => sum + file.size, 0);
    const invalid = selectedFiles.length > MAX_FILES
        || selectedFiles.some((file) => file.size > MAX_FILE_BYTES)
        || totalBytes > MAX_TOTAL_BYTES;

    if (invalid) {
        selectedFiles = [];
        fileInput.value = '';
        fileList.textContent = '文件数量或大小超出限制，请重新选择';
        uploadBtn.disabled = true;
        showStatus('error', '最多选择 5 个文件；单个不超过 10 MB，本次总大小不超过 20 MB。');
        return;
    }

    fileList.textContent = selectedFiles.length
        ? `已选择 ${selectedFiles.length} 个：${selectedFiles.map((file) => file.name).join('、')}`
        : '最多 5 个文件 · 单个不超过 10 MB';
    uploadBtn.disabled = selectedFiles.length === 0;
    statusBar.classList.add('hidden');
});

uploadBtn.addEventListener('click', async () => {
    const formData = new FormData();
    selectedFiles.forEach((file) => formData.append('files', file));
    uploadBtn.disabled = true;
    showStatus('processing', '正在安全上传资料…');

    try {
        const data = await readResponse(await fetch('/api/upload', { method: 'POST', body: formData }));
        showStatus('success', data.message);
        processBtn.disabled = false;
    } catch (error) {
        showStatus('error', `上传失败：${error.message}`);
        uploadBtn.disabled = false;
    }
});

processBtn.addEventListener('click', async () => {
    processBtn.disabled = true;
    showStatus('processing', '正在读取、切分并建立索引…');
    try {
        const data = await readResponse(await fetch('/api/process', { method: 'POST' }));
        showStatus('success', data.message);
        setKnowledgeReady(true, '资料索引已就绪，可以开始提问');
    } catch (error) {
        showStatus('error', `处理失败：${error.message}`);
        processBtn.disabled = false;
    }
});

askBtn.addEventListener('click', askQuestion);
questionInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.isComposing) askQuestion();
});

async function initializeKnowledgeStatus() {
    try {
        const status = await readResponse(await fetch('/api/status'));
        if (status.has_index) {
            setKnowledgeReady(true, '知识库已就绪，可直接提问');
            showStatus('success', '示例知识库已准备好，无需先上传文件。');
        } else {
            setKnowledgeReady(false, '请先添加并建立知识库索引');
        }
    } catch (error) {
        setKnowledgeReady(false, '暂时无法连接知识库');
        showStatus('error', `读取知识库状态失败：${error.message}`);
    }
}

function setKnowledgeReady(ready, label) {
    questionInput.disabled = !ready;
    askBtn.disabled = !ready;
    knowledgeStatus.classList.toggle('ready', ready);
    knowledgeStatus.classList.toggle('error', !ready && label.includes('无法'));
    document.getElementById('knowledgeStatus').textContent = label;
    if (ready && chatEmpty) {
        chatEmpty.querySelector('p').textContent = '可以直接提问；追问时会参考本次页面中的最近对话。';
    }
}

async function askQuestion() {
    const question = questionInput.value.trim();
    if (!question || askBtn.disabled) return;

    hideChatEmpty();
    addMessage('question', question);
    questionInput.value = '';
    questionInput.disabled = true;
    askBtn.disabled = true;
    const loadingMsg = addMessage('answer', '正在检索资料并整理回答…');

    try {
        const data = await readResponse(await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, history: conversationHistory }),
        }));
        loadingMsg.remove();
        if (data.error) {
            addMessage('error', data.error);
        } else {
            addMessage('answer', data.answer, data.sources);
            conversationHistory.push(
                { role: 'user', content: question },
                { role: 'assistant', content: data.answer }
            );
            conversationHistory = conversationHistory.slice(-10);
        }
    } catch (error) {
        loadingMsg.remove();
        addMessage('error', `请求失败：${error.message}`);
    } finally {
        questionInput.disabled = false;
        askBtn.disabled = false;
        questionInput.focus();
    }
}

async function readResponse(response) {
    let data = {};
    try { data = await response.json(); } catch { /* 用状态码生成可读提示 */ }
    if (!response.ok) {
        const detail = typeof data.detail === 'string' ? data.detail : `服务器返回 ${response.status}`;
        throw new Error(detail);
    }
    return data;
}

function showStatus(type, message) {
    statusBar.classList.remove('hidden', 'success', 'error', 'processing');
    statusBar.classList.add(type);
    statusText.textContent = message;
}

function hideChatEmpty() {
    if (chatEmpty) chatEmpty.style.display = 'none';
}

function addMessage(type, text, sources) {
    hideChatEmpty();
    const div = document.createElement('div');
    div.className = `msg ${type}`;
    const content = document.createElement('span');
    content.textContent = text;
    div.appendChild(content);

    if (sources && sources.length) {
        const details = document.createElement('details');
        details.className = 'sources';
        const summary = document.createElement('summary');
        summary.textContent = `查看检索来源（${sources.length} 条）`;
        details.appendChild(summary);
        sources.forEach((source, index) => {
            const paragraph = document.createElement('p');
            paragraph.textContent = `片段 ${index + 1}（相关度：${source.score}）：${source.text}`;
            details.appendChild(paragraph);
        });
        div.appendChild(details);
    }
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
    return div;
}

initializeKnowledgeStatus();
