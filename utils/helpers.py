def format_duration(seconds):
    if seconds is None:
        return "Live"
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def format_number(num):
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def get_progress_bar(current_time, total_time, length=20):
    if total_time == 0:
        return "━" * length

    progress = min(current_time / total_time, 1.0)
    filled = int(progress * length)
    bar = "━" * filled + "◉" + "━" * (length - filled - 1)
    return bar[:length]
