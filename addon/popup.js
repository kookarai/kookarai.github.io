document.addEventListener('DOMContentLoaded', function() {
    // Application state
    const app = {
        status: 'Not recording...',
        isRecording: false,
        audioChunks: [],
        mediaRecorder: null,
        audioSrc: null,
        datetime: '',
        phoneNumber: '',
        // Sensitive data placeholders
        modelID: "your_model_id",
        voiceID: "your_voice_id",
        apiKey: "your_elevenlabs_api_key",
        supabaseUrl: 'your_supabase_url',
        supabaseKey: 'your_supabase_anon_key',
        audioURL: null,
        scheduledEvents: [],
        voiceSettings: {
            stability: 0.5,
            similarity_boost: 0.75,
            style: 0.0,
            use_speaker_boost: true
        },
        hasuraAdminSecret: 'your_hasura_admin_secret',
        webhookURL: 'your_webhook_url'
    };

    // Get references to DOM elements
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const statusEl = document.getElementById('status');
    const audioPlayer = document.getElementById('audioPlayer');
    const phoneNumberInput = document.getElementById('phoneNumber');
    const datetimeInput = document.getElementById('datetime');
    const scheduleBtn = document.getElementById('scheduleBtn');
    const scheduledEventsDiv = document.getElementById('scheduledEvents');
    const eventsList = document.getElementById('eventsList');

    // Initialize flatpickr
    flatpickr(datetimeInput, {
        enableTime: true,
        dateFormat: "Y-m-d H:i",
        minDate: new Date(Date.now() + 60000),
        defaultDate: new Date(Date.now() + 60000),
        onChange: function(selectedDates, dateStr) {
            app.datetime = dateStr;
            updateUI();
        }
    });

    // Event listeners
    startBtn.addEventListener('click', startRecording);
    stopBtn.addEventListener('click', stopRecording);
    scheduleBtn.addEventListener('click', scheduleEvent);
    phoneNumberInput.addEventListener('input', function() {
        app.phoneNumber = phoneNumberInput.value;
        updateUI();
    });

    // Update the UI based on the app state
    function updateUI() {
        statusEl.textContent = app.status;

        if (app.audioSrc) {
            audioPlayer.style.display = 'block';
            audioPlayer.src = app.audioSrc;
        } else {
            audioPlayer.style.display = 'none';
        }

        startBtn.disabled = app.isRecording;
        stopBtn.disabled = !app.isRecording;

        scheduleBtn.disabled = !canSchedule();

        if (app.scheduledEvents.length > 0) {
            scheduledEventsDiv.style.display = 'block';
            renderScheduledEvents();
        } else {
            scheduledEventsDiv.style.display = 'none';
        }
    }

    // Check if scheduling is possible
    function canSchedule() {
        const phoneValid = /^\d{10,15}$/.test(app.phoneNumber);
        return app.audioURL && app.datetime && phoneValid;
    }

    // Start recording audio
    function startRecording() {
        app.audioSrc = null;
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                app.mediaRecorder = new MediaRecorder(stream);
                app.mediaRecorder.start();
                app.status = "Recording...";
                app.isRecording = true;
                updateUI();
                app.mediaRecorder.ondataavailable = event => {
                    app.audioChunks.push(event.data);
                };
            })
            .catch(error => {
                alert("Mic access denied: " + error.message);
            });
    }

    // Stop recording audio
    function stopRecording() {
        if (app.mediaRecorder) {
            app.mediaRecorder.stop();
            app.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(app.audioChunks, { type: "audio/webm" });
                app.audioChunks = [];
                processAudio(audioBlob);
            };
            app.isRecording = false;
            app.status = "Recording stopped.";
            updateUI();
        }
    }

    // Process the recorded audio
    function processAudio(audioBlob) {
        app.status = "Processing audio...";
        updateUI();

        const form = new FormData();
        form.append("model_id", app.modelID);
        form.append("voice_settings", JSON.stringify(app.voiceSettings));
        form.append("audio", audioBlob);

        fetch(`https://api.elevenlabs.io/v1/speech-to-speech/${app.voiceID}`, {
            method: "POST",
            headers: {
                "xi-api-key": app.apiKey
            },
            body: form
        })
        .then(response => response.blob())
        .then(blob => {
            app.status = "Audio processed.";
            app.audioSrc = URL.createObjectURL(blob);
            uploadAudio(blob);
            updateUI();
        })
        .catch(error => {
            console.error("Error processing audio:", error);
            app.status = "Error processing audio.";
            updateUI();
        });
    }

    // Upload audio to Supabase storage
    function uploadAudio(audioBlob) {
        const fileName = `audio-${Date.now()}.wav`;
        const formData = new FormData();
        formData.append('file', audioBlob, fileName);

        fetch(`${app.supabaseUrl}/storage/v1/object/audio/${fileName}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${app.supabaseKey}`,
                'apikey': app.supabaseKey
            },
            body: formData
        })
        .then(response => {
            if (response.ok) {
                app.audioURL = `${app.supabaseUrl}/storage/v1/object/public/audio/${fileName}`;
                updateUI();
            } else {
                throw new Error("Error uploading audio.");
            }
        })
        .catch(error => {
            console.error("Error uploading audio:", error);
            alert("Error uploading audio.");
        });
    }

    // Schedule the event
    function scheduleEvent() {
        const payload = { url: app.audioURL, number: app.phoneNumber };
        const scheduleAt = moment(app.datetime).utc().format();

        fetch('https://your_hasura_instance/v1/metadata', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-hasura-admin-secret': app.hasuraAdminSecret
            },
            body: JSON.stringify({
                type: "create_scheduled_event",
                args: {
                    webhook: app.webhookURL,
                    schedule_at: scheduleAt,
                    payload
                }
            })
        })
        .then(response => response.json())
        .then(() => {
            app.status = `Event scheduled at ${moment(app.datetime).format('YYYY-MM-DD HH:mm:ss')}.`;
            getScheduledEvents();
            updateUI();
        })
        .catch(error => {
            console.error("Error scheduling event:", error);
            app.status = "Error scheduling event.";
            updateUI();
        });
    }

    // Get scheduled events
    function getScheduledEvents() {
        fetch('https://your_hasura_instance/v1/metadata', {
            method: 'POST',
            headers: {
                'content-type': 'application/json',
                'x-hasura-admin-secret': app.hasuraAdminSecret
            },
            body: JSON.stringify({
                type: "get_scheduled_events",
                args: { type: "one_off", status: ["scheduled"], limit: 1001 }
            })
        })
        .then(response => response.json())
        .then(data => {
            app.scheduledEvents = data.events.map(event => ({
                datetime: event.scheduled_time,
                phoneNumber: event.payload.number,
                id: event.id
            }));
            updateUI();
        })
        .catch(error => {
            console.error('Error fetching events:', error);
        });
    }

    // Delete a scheduled event
    function deleteScheduledEvent(eventId) {
        fetch('https://your_hasura_instance/v1/metadata', {
            method: 'POST',
            headers: {
                'content-type': 'application/json',
                'x-hasura-admin-secret': app.hasuraAdminSecret
            },
            body: JSON.stringify({
                type: "delete_scheduled_event",
                args: {
                    type: "one_off",
                    event_id: eventId
                }
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(() => {
            getScheduledEvents();
        })
        .catch(error => {
            console.error(`Error deleting event ${eventId}:`, error);
        });
    }

    // Render scheduled events
    function renderScheduledEvents() {
        eventsList.innerHTML = '';
        app.scheduledEvents.forEach(event => {
            const li = document.createElement('li');
            li.className = 'flex justify-between items-center mb-2 text-white';

            const div = document.createElement('div');
            const p1 = document.createElement('p');
            p1.className = 'text-sm';
            p1.textContent = event.datetime;
            const p2 = document.createElement('p');
            p2.className = 'text-xs text-gray-400';
            p2.textContent = `Phone: ${event.phoneNumber}`;
            div.appendChild(p1);
            div.appendChild(p2);

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'bg-red-500 hover:bg-red-600 text-white py-1 px-3 rounded-lg';
            deleteBtn.textContent = 'Delete';
            deleteBtn.onclick = function() {
                deleteScheduledEvent(event.id);
            };

            li.appendChild(div);
            li.appendChild(deleteBtn);
            eventsList.appendChild(li);
        });
    }

    // Initial setup
    app.datetime = datetimeInput.value;
    app.phoneNumber = phoneNumberInput.value;
    getScheduledEvents();
    updateUI();
});
