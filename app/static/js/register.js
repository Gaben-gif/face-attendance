const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const captureBtn = document.getElementById('captureBtn');
const feedback = document.getElementById('feedback');
navigator.mediaDevices.getUserMedia({ video: true }).then(stream => {
    video.srcObject = stream;
});

captureBtn.onclick = async function () {
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(async (blob) => {
        const name = document.getElementById('name').value;
        if (!name) {
            feedback.innerText = "Enter your name!";
            return;
        }
        let formData = new FormData();
        formData.append('name', name);
        formData.append('image', blob, 'capture.jpg');
        let resp = await fetch('/api/register', { method: 'POST', body: formData });
        let data = await resp.json();
        feedback.innerText = data.msg;
    }, 'image/jpeg');
};