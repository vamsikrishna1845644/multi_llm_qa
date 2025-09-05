
document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('file-input');
    const uploadButton = document.getElementById('upload-button');
    const imagePreview = document.getElementById('image-preview');
    const resultsSection = document.getElementById('results-section');

    let selectedFiles = [];

    fileInput.addEventListener('change', (event) => {
        selectedFiles = Array.from(event.target.files);
        renderImagePreviews();
    });

    function renderImagePreviews() {
        imagePreview.innerHTML = '';
        selectedFiles.forEach(file => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const div = document.createElement('div');
                div.className = 'image-preview-item';
                const img = document.createElement('img');
                img.src = e.target.result;
                div.appendChild(img);
                imagePreview.appendChild(div);
            };
            reader.readAsDataURL(file);
        });
    }

    uploadButton.addEventListener('click', async () => {
        if (selectedFiles.length === 0) {
            alert('Please select one or more images to upload.');
            return;
        }

        uploadButton.disabled = true;
        uploadButton.textContent = 'Uploading...';
        resultsSection.innerHTML = '<p>Processing your images...</p>';

        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('uploaded_photos', file);
        });

        try {
            const response = await fetch('/api/uploads/', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            pollForResults(result.id);

        } catch (error) {
            console.error('Upload failed:', error);
            resultsSection.innerHTML = `<p class="status error">Upload failed. Please try again.</p>`;
            uploadButton.disabled = false;
            uploadButton.textContent = 'Upload and Process';
        }
    });

    async function pollForResults(uploadId) {
        resultsSection.innerHTML = `<p>Polling for results for upload ID: ${uploadId}</p>`;
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/api/uploads/${uploadId}/`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                renderResults(data);

                if (data.status === 'done' || data.status === 'error') {
                    clearInterval(interval);
                    uploadButton.disabled = false;
                    uploadButton.textContent = 'Upload and Process';
                }
            } catch (error) {
                console.error('Polling failed:', error);
                clearInterval(interval);
                resultsSection.innerHTML = `<p class="status error">Error fetching results. Please check the console.</p>`;
                uploadButton.disabled = false;
                uploadButton.textContent = 'Upload and Process';
            }
        }, 3000); // Poll every 3 seconds
    }

    function renderResults(data) {
        resultsSection.innerHTML = `<h2>Results (Status: <span class="status ${data.status}">${data.status}</span>)</h2>`;

        data.photos.forEach(photo => {
            const resultCard = document.createElement('div');
            resultCard.className = 'result-card';

            let questionText = 'Extracting text...';
            if (photo.question && photo.question.extracted_text) {
                questionText = photo.question.extracted_text;
            }

            resultCard.innerHTML = `
                <h3>Question from ${photo.filename}</h3>
                <p><strong>Extracted Text:</strong> ${questionText}</p>
                <div class="answer-grid"></div>
            `;

            const answerGrid = resultCard.querySelector('.answer-grid');

            if (photo.question && photo.question.answers) {
                photo.question.answers.forEach(answer => {
                    const answerCard = document.createElement('div');
                    answerCard.className = 'answer-card';
                    answerCard.innerHTML = `
                        <h4>${answer.provider} (${answer.model})</h4>
                        <p>${answer.content || 'No answer yet...'}</p>
                        <small>Status: <span class="status ${answer.status}">${answer.status}</span></small>
                    `;
                    answerGrid.appendChild(answerCard);
                });
            }

            resultsSection.appendChild(resultCard);
        });
    }
});
