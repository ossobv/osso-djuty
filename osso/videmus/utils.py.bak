# vim: set ts=8 sw=4 sts=4 et ai:
import datetime
from django.conf import settings
import logging
log = logging.getLogger(__name__)
import os.path
from subprocess import Popen, PIPE, STDOUT
from tempfile import NamedTemporaryFile

from django.core.files import File


ENCODING_OUTPUT = getattr(settings, 'VIDEMUS_ENCODING_OUTPUT', '/dev/null')


def get_video_metadata(file_or_path, validate=False):
    '''
    Retrieve metadata from the videofile ``file_or_path``.
    If ``validate`` is True, raise a ValueError if the file is not
    a valid video.
    '''
    width = height = bitrate = fps = length = None

    if hasattr(file_or_path, 'temporary_file_path'):
        filepath = file_or_path.temporary_file_path()
    elif hasattr(file_or_path, 'path'):
        filepath = file_or_path.path
    else:
        filepath = file_or_path

    if not os.path.isfile(filepath):
        if validate:
            raise ValueError('video metadata requires a physical file')
        return (width, height, bitrate, fps, length)

    has_video = False
    cmd = ['ffmpeg', '-i', filepath]
    # ffmpeg prints status messages to stderr
    p = Popen(cmd, stdout=PIPE, stderr=STDOUT)
    for line in p.stdout:
        line = line.strip()
        if not has_video and 'Stream' in line and 'Video' in line:
            for part in line.split(', '):
                if 'x' in part:
                    part = part.split(' ')[0]
                    try:
                        width, height = map(int, part.split('x'))
                    except ValueError:
                        pass
                elif 'kb/s' in part:
                    try:
                        bitrate = int(part.split(' ')[0])
                    except ValueError:
                        pass
                elif 'tbr' in part or 'fps' in part:
                    try:
                        fps = float(part.split(' ')[0])
                    except ValueError:
                        pass
            has_video = True
        elif 'Duration' in line:
            part = line.split(', ')[0]
            part = part.split(' ')[-1]
            part, microsecond = part.split('.')
            hour, minute, second = map(int, part.split(':'))
            try:
                length = datetime.time(hour, minute, second, int(microsecond))
            except ValueError:
                pass
            # the container bitrate, stream bitrate is preferred
            if bitrate is None:
                part = line.split(', ')[-1]
                part = part.split(' ')
                if part[-1] == 'kb/s':
                    try:
                        bitrate = int(part[-2])
                    except ValueError:
                        pass
    p.wait()
    # no output file gives an error code
    if p.returncode != 1 or (not has_video and validate):
        raise ValueError('Unable to parse video metadata: %r' % p.returncode)
    return (width, height, bitrate, fps, length)


def video_screenshot(video, width, height, callback):
    try:
        seekto = int((video.length.hour * 3600 +
                      video.length.minute * 60 +
                      video.length.second) / 5)
    except:
        seekto = 0

    NULL = open(ENCODING_OUTPUT, 'a')
    with NamedTemporaryFile(suffix='.png') as tmpfile:
        cmd = [
            'ffmpeg', '-y',     # overwrite tempfile
            '-ss', str(seekto),
            '-i', video.path,
            '-an',              # disable audio processing
            '-vframes', '1',
            '-vcodec', 'png',
            '-s', '%sx%s' % (width, height),
            tmpfile.name,
        ]
        p = Popen(cmd, stdout=NULL, stderr=NULL)
        p.wait()
        if p.returncode == 0:
            callback(tmpfile)
    if NULL is not None:
        NULL.close()


def encode_video(video_in, video_out):
    '''
    Encode ``video_in`` to ``video_out`` using the parameters on ``video_out``.
    ``video_in`` and ``video_out`` are instances of the ``VideoFile`` model.
    '''
    success = False
    with NamedTemporaryFile(suffix='.%s' % video_out.format) as tmpfile:
        video_out_name = os.path.basename(video_in.video.path)
        video_out_name, extension = os.path.splitext(video_out_name)
        video_out_name = '%s.%s' % (video_out_name, video_out.format)
        encoders = {
            'flv': encode_video_flv,
            'mp4': encode_video_mp4,
            'ogv': encode_video_ogv,
            'webm': encode_video_webm,
        }
        encoder = encoders.get(video_out.format)
        if encoder:
            success = encoder(video_in, video_out, tmpfile)
            if success:
                video_out.video.save(video_out_name, File(tmpfile), save=False)
                video_out.is_encoded = True
                video_out.save()
    return success


def video_bitrate(width):
    if width > 1900:
        return '8000k'
    elif width > 1200:
        return '5000k'
    elif width > 800:
        return '2500k'
    elif width > 600:
        return '1000k'
    return '750k'


def encode_video_flv(video_in, video_out, tmpfile):
    NULL = open(ENCODING_OUTPUT, 'a')
    cmd = [
        'ffmpeg',
        '-y',  # overwrite the tmpfile
        '-i', video_in.video.path,
        '-s', '%sx%s' % (video_out.width, video_out.height),
        '-b:v', video_bitrate(video_out.width),
        '-c:a', 'libmp3lame', '-ac', '2', '-q:a', '3',
        '-movflags', '+faststart',
        tmpfile.name,
    ]
    p = Popen(cmd, stdout=NULL, stderr=NULL)
    p.wait()
    if p.returncode == 0:
        cmd = ['flvtool2', '-U', tmpfile.name]
        p = Popen(cmd, stdout=NULL, stderr=NULL)
        p.wait()
    if NULL is not None:
        NULL.close()
    return p.returncode == 0


def encode_video_mp4(video_in, video_out, tmpfile):
    NULL = open(ENCODING_OUTPUT, 'a')
    cmd = [
        'ffmpeg', '-y', '-i', video_in.video.path,
        '-s', '%sx%s' % (video_out.width, video_out.height),
        '-c:v', 'libx264',
        '-b:v', video_bitrate(video_out.width),
        '-c:a', 'libfdk_aac', '-ac', '2', '-vbr', '3',
        '-movflags', '+faststart',
        tmpfile.name,
    ]
    p = Popen(cmd, stdout=NULL, stderr=NULL)
    p.wait()
    if NULL is not None:
        NULL.close()
    return p.returncode == 0


def encode_video_ogv(video_in, video_out, tmpfile):
    NULL = open(ENCODING_OUTPUT, 'a')
    cmd = [
        'ffmpeg', '-y', '-i', video_in.video.path,
        '-s', '%sx%s' % (video_out.width, video_out.height),
        '-c:v', 'libtheora', '-g', '15', '-qscale:v', '7',
        '-b:v', video_bitrate(video_out.width),
        '-c:a', 'libvorbis', '-ac', '2', '-qscale:a', '5',
        '-movflags', '+faststart',
        tmpfile.name,
    ]
    p = Popen(cmd, stdout=NULL, stderr=NULL)
    p.wait()
    if NULL is not None:
        NULL.close()
    return p.returncode == 0


def encode_video_webm(video_in, video_out, tmpfile):
    NULL = open(ENCODING_OUTPUT, 'a')
    cmd = [
        'ffmpeg', '-y', '-i', video_in.video.path,
        '-s', '%sx%s' % (video_out.width, video_out.height),
        '-c:v', 'libvpx', '-g', '15',
        '-crf', '20', '-b:v', video_bitrate(video_out.width),
        '-c:a', 'libvorbis', '-ac', '2', '-qscale:a', '5',
        '-movflags', '+faststart',
        tmpfile.name,
    ]
    p = Popen(cmd, stdout=NULL, stderr=NULL)
    p.wait()
    if NULL is not None:
        NULL.close()
    return p.returncode == 0
