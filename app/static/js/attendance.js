const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const markBtn = document.getElementById('markBtn');
const feedback = document.getElementById('feedback');
navigator.mediaDevices.getUserMedia({ video: true }).then(stream => {
    video.srcObject = stream;
});

markBtn.onclick = async function () {
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(async (blob) => {
        let formData = new FormData();
        formData.append('image', blob, 'capture.jpg');
        let resp = await fetch('/api/mark_attendance', { method: 'POST', body: formData });
        let data = await resp.json();
        feedback.innerText = data.msg;
    }, 'image/jpeg');
};