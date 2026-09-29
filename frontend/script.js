const CHAT_API_URL =
    "http://127.0.0.1:8000/chat";

const PDF_UPLOAD_URL =
    "http://127.0.0.1:8000/upload-pdf";

const PDF_ASK_URL =
    "http://127.0.0.1:8000/ask-pdf";

const AKHIL_ASK_URL =
    "http://127.0.0.1:8000/ask-akhil";

const ROUTER_API_URL = 
    "http://127.0.0.1:8000/route-chat";

/* ========================================= */
/* CHAT STORAGE */
/* ========================================= */

let chats =
    JSON.parse(
        localStorage.getItem("akhilAI_chats")
    ) || [];

let currentChatId =
    localStorage.getItem(
        "akhilAI_currentChatId"
    ) || null;



/* ========================================= */
/* PDF + CHAT MODE */
/* ========================================= */

let pdfUploaded = false;

let chatMode = "normal";
// normal = Normal AI Chat
// pdf    = PDF Chat
// akhil  = Ask About Akhil



/* ========================================= */
/* SAVE CHATS */
/* ========================================= */

function saveChats() {

    localStorage.setItem(
        "akhilAI_chats",
        JSON.stringify(chats)
    );

    if (currentChatId) {

        localStorage.setItem(
            "akhilAI_currentChatId",
            currentChatId
        );

    }

}



/* ========================================= */
/* CREATE CHAT */
/* ========================================= */

function createChat() {

    const chat = {

        id: Date.now().toString(),

        title: "New Chat",

        messages: []

    };


    chats.unshift(chat);

    currentChatId = chat.id;

    saveChats();

    renderChatList();

    renderCurrentChat();

}



/* ========================================= */
/* GET CURRENT CHAT */
/* ========================================= */

function getCurrentChat() {

    return chats.find(
        chat =>
            chat.id === currentChatId
    );

}



/* ========================================= */
/* ADD MESSAGE TO UI */
/* ========================================= */

function addMessage(
    text,
    sender
) {

    const chatMessages =
        document.getElementById(
            "chatMessages"
        );


    const messageDiv =
        document.createElement(
            "div"
        );


    messageDiv.classList.add(
        "message",
        sender
    );


    messageDiv.textContent = text;


    chatMessages.appendChild(
        messageDiv
    );


    chatMessages.scrollTop =
        chatMessages.scrollHeight;

}



/* ========================================= */
/* RENDER CHAT LIST */
/* ========================================= */

function renderChatList() {

    const chatList =
        document.getElementById(
            "chatList"
        );


    if (!chatList) {
        return;
    }


    chatList.innerHTML = "";


    chats.forEach(chat => {

        const chatItem =
            document.createElement(
                "button"
            );


        chatItem.className =
            "chat-history-item";


        chatItem.textContent =
            "💬 " + chat.title;


        chatItem.onclick = () => {

            currentChatId =
                chat.id;

            saveChats();

            renderChatList();

            renderCurrentChat();

        };


        if (
            chat.id ===
            currentChatId
        ) {

            chatItem.classList.add(
                "active"
            );

        }


        chatList.appendChild(
            chatItem
        );

    });

}



/* ========================================= */
/* RENDER CURRENT CHAT */
/* ========================================= */

function renderCurrentChat() {

    const chatMessages =
        document.getElementById(
            "chatMessages"
        );


    chatMessages.innerHTML = "";


    const chat =
        getCurrentChat();


    if (
        !chat ||
        chat.messages.length === 0
    ) {

        chatMessages.innerHTML = `

            <div
                class="welcome"
                id="welcomeMessage"
            >

                <div class="bot-icon">
                    🤖
                </div>

                <h1>
                    How can I help you?
                </h1>

                <p>
                    Ask me anything, upload a PDF,
                    or ask about Akhil.
                </p>

            </div>

        `;

        return;

    }


    chat.messages.forEach(
        message => {

            addMessage(
                message.content,
                message.role
            );

        }
    );

}



/* ========================================= */
/* CHAT MODE */
/* ========================================= */

function setChatMode(mode) {

    const normalBtn =
        document.getElementById(
            "normalModeBtn"
        );


    const pdfBtn =
        document.getElementById(
            "pdfModeBtn"
        );


    const akhilBtn =
        document.getElementById(
            "akhilModeBtn"
        );


    const modeStatus =
        document.getElementById(
            "modeStatus"
        );


    const messageInput =
        document.getElementById(
            "messageInput"
        );


    if (
        !normalBtn ||
        !pdfBtn ||
        !akhilBtn ||
        !modeStatus ||
        !messageInput
    ) {

        console.error(
            "Chat mode elements not found in HTML."
        );

        return;

    }



    /* =============================== */
    /* PDF MODE VALIDATION */
    /* =============================== */

    if (
        mode === "pdf" &&
        !pdfUploaded
    ) {

        alert(
            "Please upload a PDF first."
        );

        chatMode = "normal";

        return;

    }



    /* =============================== */
    /* SET MODE */
    /* =============================== */

    chatMode = mode;



    /* =============================== */
    /* REMOVE ACTIVE CLASS */
    /* =============================== */

    normalBtn.classList.remove(
        "active"
    );

    pdfBtn.classList.remove(
        "active"
    );

    akhilBtn.classList.remove(
        "active"
    );



    /* =============================== */
    /* NORMAL MODE */
    /* =============================== */

    if (
        chatMode === "normal"
    ) {

        normalBtn.classList.add(
            "active"
        );


        modeStatus.textContent =
            "Normal AI Assistant";


        messageInput.placeholder =
            "Message Akhil AI...";

    }



    /* =============================== */
    /* PDF MODE */
    /* =============================== */

    else if (
        chatMode === "pdf"
    ) {

        pdfBtn.classList.add(
            "active"
        );


        modeStatus.textContent =
            "PDF Chat";


        messageInput.placeholder =
            "Ask a question about the PDF...";

    }



    /* =============================== */
    /* AKHIL MODE */
    /* =============================== */

    else if (
        chatMode === "akhil"
    ) {

        akhilBtn.classList.add(
            "active"
        );


        modeStatus.textContent =
            "Ask About Akhil";


        messageInput.placeholder =
            "Ask anything about Akhil...";

    }

}



/* ========================================= */
/* UPLOAD PDF */
/* ========================================= */

async function uploadPDF() {

    const input =
        document.getElementById(
            "pdfInput"
        );


    const status =
        document.getElementById(
            "pdfStatus"
        );


    const modeStatus =
        document.getElementById(
            "modeStatus"
        );


    if (
        !input.files ||
        input.files.length === 0
    ) {

        return;

    }


    const file =
        input.files[0];



    /* =============================== */
    /* VALIDATE FILE */
    /* =============================== */

    if (
        file.type !==
        "application/pdf"
    ) {

        status.textContent =
            "❌ Please select a PDF file.";

        return;

    }


    status.textContent =
        "⏳ Uploading and processing...";


    const formData =
        new FormData();


    formData.append(
        "file",
        file
    );


    try {

        const response =
            await fetch(
                PDF_UPLOAD_URL,
                {
                    method: "POST",
                    body: formData
                }
            );


        const data =
            await response.json();



        /* =============================== */
        /* SUCCESS */
        /* =============================== */

        if (
            data.success
        ) {

            pdfUploaded = true;


            status.textContent =
                "✅ " +
                data.filename +
                " (" +
                data.chunk_count +
                " chunks)";


            modeStatus.textContent =
                chatMode === "pdf"
                    ? "PDF Chat"
                    : chatMode === "akhil"
                        ? "Ask About Akhil"
                        : "Normal AI Assistant";


            console.log(
                "PDF uploaded successfully:",
                data.filename
            );

        }



        /* =============================== */
        /* FAILURE */
        /* =============================== */

        else {

            pdfUploaded = false;


            status.textContent =
                "❌ " +
                data.message;

        }

    }


    catch (error) {

        console.error(
            "PDF Upload Error:",
            error
        );


        pdfUploaded = false;


        status.textContent =
            "❌ PDF upload failed.";

    }

}



/* ========================================= */
/* SEND MESSAGE */
/* ========================================= */

async function sendMessage() {

    const messageInput =
        document.getElementById(
            "messageInput"
        );

    const sendButton =
        document.getElementById(
            "sendButton"
        );

    const message =
        messageInput.value.trim();

    if (!message) {
        return;
    }


    /* =============================== */
    /* CREATE CHAT IF NEEDED */
    /* =============================== */

    if (!currentChatId) {
        createChat();
    }

    const chat = getCurrentChat();


    /* =============================== */
    /* REMOVE WELCOME */
    /* =============================== */

    const welcomeMessage =
        document.getElementById(
            "welcomeMessage"
        );

    if (welcomeMessage) {
        welcomeMessage.remove();
    }


    /* =============================== */
    /* SAVE USER MESSAGE */
    /* =============================== */

    chat.messages.push({
        role: "user",
        content: message
    });


    /* =============================== */
    /* CHAT TITLE */
    /* =============================== */

    if (chat.messages.length === 1) {

        chat.title =
            message.length > 30
                ? message.substring(0, 30) + "..."
                : message;

    }


    addMessage(
        message,
        "user"
    );

    saveChats();
    renderChatList();

    messageInput.value = "";
    sendButton.disabled = true;


    try {

        /* ================================= */
        /* AUTOMATIC INTENT ROUTER */
        /* ================================= */

        const history =
            chat.messages
                .slice(0, -1)
                .map(message => ({
                    role: message.role,
                    content: message.content
                }));


        const response =
            await fetch(
                ROUTER_API_URL,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            message: message,
                            history: history
                        })
                }
            );


        const data =
            await response.json();


        /* ================================= */
        /* ROUTER SUCCESS */
        /* ================================= */

        if (data.success) {

            chat.messages.push({
                role: "assistant",
                content: data.answer
            });


            addMessage(
                data.answer,
                "assistant"
            );


            saveChats();

            renderChatList();


            /* ================================= */
            /* SHOW DETECTED INTENT IN CONSOLE */
            /* ================================= */

            console.log(
                "Automatic Intent:",
                data.intent
            );

        }


        /* ================================= */
        /* ROUTER ERROR */
        /* ================================= */

        else {

            addMessage(
                data.answer ||
                    "Something went wrong.",
                "assistant"
            );

        }

    }


    catch (error) {

        console.error(
            "Router Error:",
            error
        );


        addMessage(
            "Sorry bro, something went wrong. Please check the backend.",
            "assistant"
        );

    }


    sendButton.disabled = false;

    messageInput.focus();

}


/* ========================================= */
/* ENTER KEY */
/* ========================================= */

function handleKeyDown(event) {

    if (
        event.key === "Enter" &&
        !event.shiftKey
    ) {

        event.preventDefault();

        sendMessage();

    }

}



/* ========================================= */
/* NEW CHAT */
/* ========================================= */

function newChat() {

    createChat();

}



/* ========================================= */
/* INITIALIZE */
/* ========================================= */

if (!currentChatId) {

    if (
        chats.length > 0
    ) {

        currentChatId =
            chats[0].id;

    }

    else {

        createChat();

    }

}


renderChatList();

renderCurrentChat();



/* ========================================= */
/* DEFAULT MODE */
/* ========================================= */

setChatMode("normal");



/* ========================================= */
/* MODE BUTTON EVENTS */
/* ========================================= */

const normalModeBtn =
    document.getElementById(
        "normalModeBtn"
    );


const pdfModeBtn =
    document.getElementById(
        "pdfModeBtn"
    );


const akhilModeBtn =
    document.getElementById(
        "akhilModeBtn"
    );


if (normalModeBtn) {

    normalModeBtn.addEventListener(
        "click",
        () => setChatMode("normal")
    );

}


if (pdfModeBtn) {

    pdfModeBtn.addEventListener(
        "click",
        () => setChatMode("pdf")
    );

}


if (akhilModeBtn) {

    akhilModeBtn.addEventListener(
        "click",
        () => setChatMode("akhil")
    );

}