# vim: set ts=8 sw=4 sts=4 et ai:
import logging
log = logging.getLogger(__name__)
from celery.task import subtask, task, TaskSet
from celery.result import TaskSetResult


from osso.videmus.models import Video, VideoFile, VideoSetting
from osso.videmus.utils import encode_video as real_encode_video


@task
def join_taskset(setid, callback, interval=10, max_retries=None, propagate=True):
    '''
    Task to poll if the TaskSet ``setid`` has finished.

    Pass results of the TaskSet to ``callback``.
    '''
    result = TaskSetResult.restore(setid)
    if result.ready():
        return subtask(callback).delay(result.join(propagate=propagate))
    join_taskset.retry(countdown=interval, max_retries=max_retries)


@task(ignore_result=True)
def encode_video(cls, video_pk):
    '''
    Task to encode a ``Video`` into one ore more ``VideoFile``'s.
    '''
    try:
        video_obj = cls.objects.get(pk=video_pk)
    except cls.DoesNotExist:
        # video was removed
        return

    filecls = video_obj.videofile_set.model

    files = list(video_obj.videofile_set.all())

    if video_obj.is_encoded and all(vfile.is_encoded for vfile in files):
        # video has been processed
        return

    video = video_obj.video

    # a video is required to meet requirments
    # to be encoded in specific a resolution
    if len(files) == 0:
        for setting in VideoSetting.objects.all():
            if video.width >= setting.width or video.height >= setting.height:
                vfile = filecls.objects.create(original=video_obj,\
                        format=setting.format,\
                        width=setting.width, height=setting.height)
                files.append(vfile)
                log.info('%r can be encoded to %r' % (video, setting))

    tasks = []
    for vfile in files:
        if vfile.is_encoded:
            continue
        if vfile.width > 600 or vfile.height > 300:
            encode_video_file.delay(filecls, vfile.pk)
        else:
            task = encode_video_file_quick.subtask(args=(filecls, vfile.pk))
            tasks.append(task)

    # create a taskset of the quick encodings
    job = TaskSet(tasks=tasks)
    result = job.apply_async()
    result.save()

    # start the publish_video callback when the taskset completes
    callback = publish_video.subtask(args=(cls, video_pk))
    # max_tries has to be set otherwise it uses the default
    # check every 60 seconds if the set has completed
    join_taskset.delay(result.taskset_id, callback, interval=60, max_retries=300, propagate=False)


# these tasks are identical except for what they process.
# by putting quick encodes into a separate task we can
# put them in a separate queue.
# This will avoid the situation where all active tasks
# are high quality encodes.
@task
def encode_video_file_quick(cls, vfile_pk):
    # call the function below directly
    return encode_video_file(cls, vfile_pk)


@task
def encode_video_file(cls, vfile_pk):
    '''
    Encode ``original`` to VideoFile ``vfile_pk``.
    '''
    try:
        vfile = cls.objects.get(pk=vfile_pk)
    except cls.DoesNotExist:
        # VideoFile was removed
        return False
    return real_encode_video(vfile.original, vfile)


@task(ignore_result=True)
def publish_video(results, cls, video_pk):
    '''
    Publish Video ``video_pk`` if encoding was successful.
    '''
    try:
        video = cls.objects.get(pk=video_pk)
    except cls.DoesNotExist:
        return

    log.debug('publication of %r: %r' % (video, results))

    if len([r for r in results if r == True]) == len(results):
        video.is_encoded = True
        video.save()
        log.info('quick encoding of %r completed' % video)
    else:
        log.error('quick encoding of %r failed: %r' % (video, results))
