console.log("I am working");

const blogContent = document.getElementById('blogContent');
const generatedBlock = document.getElementById('generated-block');
const generateBlogButton = document.getElementById('generateBlogButton');
//warning, loading_circle are handled in if block
const warning = document.getElementById('warning-on-process');
const loading_circle = document.getElementById('loading-circle');

const invalid_url_error = document.getElementById('error-invalid-yt-url');
const empty_url_error = document.getElementById('error-empty-yt-url');

window.onload = ()=>{
    generateBlogButton.addEventListener('click', generateHandler);
    invalid_url_error.classList.add('hidden');
    empty_url_error.classList.add('hidden');
}
function disableButton(id) {
    document.getElementById(id).disabled = true;
}
function enableButton(id){
    document.getElementById(id).disabled = false;
}
// scope to implement the cancel button when performing generation
function cancelGeneration(){
    console.log("Perform cancel operation while fetching from server");
    
}
async function generateHandler(event){
    event.preventDefault();
    const youtubeLink = document.getElementById('youtubeLink').value;
    console.log("GENERATE");
    console.log(youtubeLink);
    error_flag = false;
    if (youtubeLink) {
        warning.classList.remove('hidden');
        loading_circle.style.display = 'block';
        disableButton("generateBlogButton");
        generateBlogButton.innerText = 'Cancel';
        generateBlogButton.disabled = true;
        generatedBlock.classList.add('hidden');
        blogContent.innerHTML = ''; // Clear previous content

        const endpointUrl = '/generate-blog/';
        
        try {
            const response = await fetch(endpointUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ link: youtubeLink })
            });
            
            const data = await response.json();
            
            blogContent.innerHTML = data.content;
            
        } catch (error) {
            error_flag = true;
            console.error("Error occurred:", error);
            //alert("Something went wrong. Please try again later.");
            invalid_url_error.classList.remove('hidden')

        }
        loading_circle.style.display = 'none';
        enableButton("generateBlogButton");
        warning.classList.add('hidden');
        generateBlogButton.innerText = 'Generate';

    } else {
        //alert("Please enter a YouTube link.");
        empty_url_error.classList.remove('hidden')
    }
    if (!error_flag)
        generatedBlock.classList.remove('hidden');
}

// document.getElementById('generateBlogButton').addEventListener('click', generateHandler);

let mediaRecorder = null;
let mediaStream = null;
let audioChunks = [];
let isRecording = false;

// timer variables
let timerInterval = null;
let elapsedSeconds = 0;
const MAX_SECONDS = 5 * 60; // 5 minutes

const recordBtn = document.getElementById("recordBtn");
const recordStatus = document.getElementById("recordStatus");
const timerEl = document.getElementById("timer");
const audioPlayer = document.getElementById("audioPlayer");

recordBtn.addEventListener("click", async () => {

    // START RECORDING
    if (!isRecording) {
        try {
            mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch {
            alert("Microphone permission denied");
            return;
        }

        mediaRecorder = new MediaRecorder(mediaStream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = () => {
    recordedAudioBlob = new Blob(audioChunks, { type: "audio/webm" });

    audioPlayer.src = URL.createObjectURL(recordedAudioBlob);
    audioPlayer.classList.remove("hidden");

    document.getElementById("generateAudioBtn").disabled = false;

    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
};


        mediaRecorder.start();
        isRecording = true;

        // UI → STOP
        recordBtn.innerText = "⏸️";
        recordBtn.classList.replace("bg-red-600", "bg-gray-800");
        recordStatus.innerText = "Recording…";

        // start timer
        startTimer();
    }

    // STOP RECORDING (manual)
    else {
        stopRecording("Recorded — play below");
    }
});

function startTimer() {
    elapsedSeconds = 0;
    timerEl.innerText = "00:00";

    timerInterval = setInterval(() => {
        elapsedSeconds++;

        const minutes = String(Math.floor(elapsedSeconds / 60)).padStart(2, "0");
        const seconds = String(elapsedSeconds % 60).padStart(2, "0");
        timerEl.innerText = `${minutes}:${seconds}`;

        // auto-stop at 5 minutes
        if (elapsedSeconds >= MAX_SECONDS) {
            stopRecording("Recording stopped at 5 minutes");
        }
    }, 1000);
}

function stopRecording(statusText) {
    if (!isRecording) return;

    isRecording = false;
    clearInterval(timerInterval);
    timerInterval = null;

    mediaRecorder.stop();

    // reset UI
    recordBtn.innerText = "▶️";
    recordBtn.classList.replace("bg-gray-800", "bg-red-600");
    recordStatus.innerText = statusText;
}
const generateAudioBtn = document.getElementById("generateAudioBtn");

generateAudioBtn.addEventListener("click", async () => {
    if (!recordedAudioBlob) {
        alert("No audio recorded");
        return;
    }

    warning.classList.remove("hidden");
    loading_circle.style.display = "block";
    generateAudioBtn.disabled = true;

    const formData = new FormData();
    formData.append("audio", recordedAudioBlob, "recorded_audio.webm");

    try {
        const response = await fetch("/generate-blog-audio/", {
            method: "POST",
            body: formData
        });
        
        const data = await response.json();
        blogContent.innerHTML = data.content;
        generatedBlock.classList.remove("hidden");

    } catch (err) {
        alert("Failed to generate blog from audio");
        console.error(err);
    }

    loading_circle.style.display = "none";
    warning.classList.add("hidden");
    generateAudioBtn.disabled = false;
});
