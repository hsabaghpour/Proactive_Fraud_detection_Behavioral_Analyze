class BehavioralDataCollector {
    constructor(apiEndpoint) {
        this.apiEndpoint = apiEndpoint;
        this.sessionId = this._generateSessionId();
        this.keystrokeBuffer = [];
        this.mouseBuffer = [];
        this.sessionStart = Date.now();
        this.bufferSize = 50; // Send data when buffer reaches this size
        this.setupEventListeners();
        console.log('BehavioralDataCollector initialized with session ID:', this.sessionId);
    }

    _generateSessionId() {
        return Math.random().toString(36).substring(2, 15) +
               Math.random().toString(36).substring(2, 15);
    }

    setupEventListeners() {
        // Keyboard events
        document.addEventListener('keydown', (e) => this._handleKeystroke(e, 'keydown'));
        document.addEventListener('keyup', (e) => this._handleKeystroke(e, 'keyup'));

        // Mouse events
        document.addEventListener('mousemove', (e) => this._handleMouseMove(e));
        document.addEventListener('click', (e) => this._handleMouseClick(e));
        
        // Send data periodically and before page unload
        setInterval(() => this.sendData(), 5000);
        window.addEventListener('beforeunload', () => this.sendData());
    }

    _handleKeystroke(event, eventType) {
        // Don't collect actual keys for privacy, just timing and key codes
        const keystrokeData = {
            event_type: eventType,
            key_code: event.keyCode,
            timestamp: Date.now() / 1000
        };

        this.keystrokeBuffer.push(keystrokeData);
        if (this.keystrokeBuffer.length >= this.bufferSize) {
            this.sendData();
        }
    }

    _handleMouseMove(event) {
        const mouseData = {
            type: 'movement',
            x: event.clientX,
            y: event.clientY,
            timestamp: Date.now() / 1000
        };

        this.mouseBuffer.push(mouseData);
        if (this.mouseBuffer.length >= this.bufferSize) {
            this.sendData();
        }
    }

    _handleMouseClick(event) {
        const clickData = {
            type: 'click',
            x: event.clientX,
            y: event.clientY,
            button: event.button,
            timestamp: Date.now() / 1000
        };

        this.mouseBuffer.push(clickData);
        this.sendData();
    }

    _collectDeviceInfo() {
        return {
            screen_resolution: `${window.screen.width}x${window.screen.height}`,
            browser_language: navigator.language,
            timezone_offset: new Date().getTimezoneOffset(),
            platform: navigator.platform,
            is_mobile: /Mobile|Android|iPhone/i.test(navigator.userAgent)
        };
    }

    async sendData() {
        if (this.keystrokeBuffer.length === 0 && this.mouseBuffer.length === 0) {
            return;
        }

        console.log('Sending behavioral data...');
        const sessionData = {
            session_id: this.sessionId,
            timestamp: new Date().toISOString(),
            session_duration: (Date.now() - this.sessionStart) / 1000,
            keystroke_data: [...this.keystrokeBuffer],
            mouse_data: [...this.mouseBuffer],
            device_info: this._collectDeviceInfo()
        };

        try {
            console.log('Sending data to server:', sessionData);
            const response = await fetch(`${this.apiEndpoint}/collect`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(sessionData)
            });

            if (response.ok) {
                console.log('Data sent successfully');
                // Clear buffers only if data was successfully sent
                this.keystrokeBuffer = [];
                this.mouseBuffer = [];
            } else {
                console.error('Failed to send behavioral data:', await response.text());
            }
        } catch (error) {
            console.error('Error sending behavioral data:', error);
        }
    }

    async analyzeSession() {
        console.log('Analyzing session:', this.sessionId);
        try {
            const response = await fetch(`${this.apiEndpoint}/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.sessionId
                })
            });

            if (response.ok) {
                const result = await response.json();
                console.log('Analysis result:', result);
                return result;
            } else {
                const errorText = await response.text();
                console.error('Failed to analyze session:', errorText);
                return null;
            }
        } catch (error) {
            console.error('Error analyzing session:', error);
            return null;
        }
    }
}

// Example usage:
// const collector = new BehavioralDataCollector('http://localhost:5000');
// Later, you can analyze the session:
// const analysis = await collector.analyzeSession(); 