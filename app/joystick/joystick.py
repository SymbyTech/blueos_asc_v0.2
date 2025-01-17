from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

# Handle WebSocket connection and data
@socketio.on('joystick_data')
def handle_joystick_data(data):
    # print('Received joystick data:', data)
    # Optionally send it back to all connected clients
    emit('joystick_response', data, broadcast=True)

if __name__ == '__main__':
    import eventlet
    import eventlet.wsgi
    socketio.run(app, port=9009, host='0.0.0.0')
