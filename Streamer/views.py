from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect,StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.template import loader
from django.urls import reverse
from django.utils import timezone
from .models import Camera, Stream
# from rq import Queue
# from rq.job import Job
# from worker import conn
# import redis
import os,base64, time
import datetime
from PIL import Image

FV = None
# q = Queue('high', default_timeout=8,connection=conn)
# r = redis.StrictRedis()
# p = r.pubsub(ignore_subscribe_messages=True)

save_streams = False
# app.config["TEMPLATES_AUTO_RELOAD"] = True

def import_data(request):
    img = None
    id = 0
    try:
        if 'image' in request.FILES:
            img = request.FILES['image'].read()
            id = int(request.POST.get('id'))
    except KeyError as e:
        raise ValidationError('Invalid image: Operation failed')
    return img, id

def addImgData(data):
    r.zadd('frame'+data['camera_id'], int(data['id']), data['image'])
    if save_streams == True:
        saveVideo(data)

def saveFile(data):
    try:
        image = base64.b64decode(data['image'])
        basepath = os.path.join('Streamer','camera',str(data['camera_id']))
        if not os.path.exists(basepath):
            os.mkdir(basepath)
        path = os.path.join(basepath,'frame_%i.jpg'%data['id'])
        f = open(path,'wb')
        f.write(image)
        return path
    except KeyError as e:
        abort(503)
        return None

def saveVideo(data):
    try:
        image = base64.b64decode(data['image'])
        basepath = os.path.join('Streamer','camera',str(data['camera_id']))
        if not os.path.exists(basepath):
            os.mkdir(basepath)
        path = os.path.join(basepath,'frame_%i.jpg'%data['id'])
        f = open(path,'wb')
        f.write(image)
        return path
    except KeyError as e:
        abort(503)
        return None

def index(request):
    """
        Display the default welcome page for the Streamer App.

        **Template:** :file:`Streamer/index.html`

    """
    cameras = Camera.objects.all()
    context = {'cameras':cameras,}
    return render(request, 'Streamer/index.html', context)

def get_camera(request):
    """
            :param selected camera id camera_id:
    """
    if request.method == 'POST':
        camera_id = request.POST['camera_dropdown']
        return HttpResponseRedirect(reverse('Streamer:camera_stream', kwargs={'camera_id':camera_id}))
    else:
        return HttpResponseRedirect(reverse('Streamer:index'))

def generateStream(camera_id):
    p.subscribe('stream')
    max_seen = 0
    frame_rate = 6.0
    last_access = time.time()
    print("Client connected!")
    while True:
        try:
            # time.sleep(1.0/frame_rate)
            result = r.zrangebyscore('frame'+str(camera_id), max_seen,'+inf')
            if result == None or result == [] or (r.getbit('stream',camera_id)==0 and len(result) <50):
                # Disconnect client if the stream has been inactive for more than 2 minutes.
                if time.time() - last_access > 120:
                    print("Inactive Stream!!")
                    break
                continue
            if time.time() - last_access <= 1.0/frame_rate:
                print("skipping frame")
                continue
            last_access = time.time()
            frame = base64.b64decode(result[0])
            id = int(r.zscore('frame'+str(camera_id),result[0]))
            max_seen = max(id,max_seen)
            r.zremrangebyscore('frame'+str(camera_id), 0, max_seen)
            print("yielding frame ",id)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except:
            print("some exception")
    print("Disconnecting client!")
    p.unsubscribe('stream')

def live_feed(request, camera_id):
    """
            :param camera_id:
    """
    resp = StreamingHttpResponse(generateStream(camera_id),
                    content_type='multipart/x-mixed-replace; boundary=frame')
    print(resp)
    resp['Cache-Control'] = 'no-cache,no-store,max-age=0,must-revalidate'
    # resp['Connection'] = 'keep-alive'
    resp['Access-Control-Allow-Origin'] = '*'
    return resp

def camera_stream(request, camera_id):
    """
            :param camera_id:
    """
    camera = get_object_or_404(Camera,pk=camera_id)
    context = {'camera_id':camera.ID}
    return render(request,'Streamer/video_feed.html', context)

@csrf_exempt
def start_stream(request,camera_id):
    """
        Indcates that Camera - :camera_id is going to start streaming now
        It will set the redis bit 'stream' with offset - camera_id to 1

        :param camera_id:
    """
    print(request)
    if request.method == 'POST':
        r.setbit('stream',camera_id,1) # indicate that streaming has begun
        camera,res = Camera.objects.get_or_create(ID=camera_id)
        print("start stream for camera", camera_id, res,camera)
        r.zremrangebyscore('frame'+str(camera_id), '-inf', '+inf')
        # stream = Stream(camera = camera)
        # stream.startTime = timezone.now()
        # stream.video_path = os.path.join('Streamer','camera',str(camera_id))

        # stream.endTime = datetime.datetime.now(tz=timezone.utc)
        # print("stream.startTime")
        # import pdb; pdb.set_trace()
        # stream.save()
        # print("saved")
        # stream.video_path = os.path.join('Streamer','camera',str(camera_id), string(stream.id))
        # print(stream)
        return HttpResponse("starting stream %s" %camera_id)

@csrf_exempt
def stop_stream(request,camera_id):
    """
        Indcates that Camera - :camera_id is going to stop streaming now
        It will set the redis bit 'stream' with offset - camera_id to 0

        :param camera_id:
    """
    print(request)
    if request.method == 'POST':
        r.setbit('stream',camera_id,0)
        camera = get_object_or_404(Camera,pk=camera_id)
        result = Stream.objects.filter(camera=camera).order_by('-startTime')
        print(result)
        return HttpResponse("stopping stream %s" %camera_id)

@csrf_exempt
def upload_stream(request, camera_id):
    print(request)
    if request.method == 'POST':
        # subs_count = r.execute_command('PUBSUB', 'NUMSUB', 'stream')
        subs_count = [0,1]
        img,id  = import_data(request)
        if img == None:
            print("Not an image!!")
        # if int(id)==0:
        #     r.getset('frame'+str(camera_id)+'base', 1)
        # else:
        #     base = r.get('frame'+str(camera_id)+'base')
            # baseimg = Image.open(io.BytesIO(base))
        image_data = base64.b64encode(img)
        data = {'camera_id':str(camera_id), 'image':image_data, 'id':int(id), 'stream_id':int}
        if int(subs_count[1]) == 0:
            saveVideo(data)
            print("No clients listening. Discarding stream data.")
        else:
            q.enqueue(addImgData,data, timeout = 10, ttl=10,  result_ttl = 10)
        return HttpResponse("uploading images to stream %s"%camera_id)
    else:
        return HttpResponse("You need to upload images here!")
