from collections import deque


FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


class MusicPlayer:
    def __init__(self):
        self.queue = deque()
        self.history = deque()
        self.current = None
        self.voice_client = None
        self.channel = None
        self.message = None
        self.requester = None
        self.volume = 1.0
        self.paused = False
        self.loop = False
        self.shuffle = False
        self.start_time = None
