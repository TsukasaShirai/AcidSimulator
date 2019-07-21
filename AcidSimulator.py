from objc_util import *
from scene import *
from PIL import Image
import ctypes
import ui, io, os
import tempfile
import sound

acid_shader = '''
	precision highp float;
	varying vec2 v_tex_coord;
	uniform sampler2D u_texture;
	uniform float u_scale;
	uniform vec2 u_sprite_size;
	uniform float u_time;
	uniform float  param;
	void main(void) {
		vec2 uv = v_tex_coord;
		uv.y += sin(uv.x * 5.0 + u_time * 2.0) * 0.05 * param;
		uv.x += sin(uv.y * 5.0 + u_time * 2.0) * 0.05 * param;
		vec2 rgb_shift = vec2(sin(u_time*2.0) * 5.0, cos(u_time*1.5) * 5.0);
		vec2 uv_r = vec2(uv.x - (param * 2.0 /u_sprite_size.x) * rgb_shift.x, uv.y - (param * 2.0/u_sprite_size.y) * rgb_shift.y); 
		vec2 uv_b = vec2(uv.x + (param * 2.0 /u_sprite_size.x) * rgb_shift.x, uv.y - (param * 2.0/u_sprite_size.y) * rgb_shift.y);
		float r = texture2D(u_texture, uv_r).r;
		float g = texture2D(u_texture, uv).g;
		float b = texture2D(u_texture, uv_b).b;
		gl_FragColor = vec4(r, g, b, 0.);
		}
		'''
		
data = None

def captureOutput_didOutputSampleBuffer_fromConnection_(_self, _cmd, _output, _sample_buffer, _conn):
	global  data
	
	imageBuffer = c.CMSampleBufferGetImageBuffer
	imageBuffer.argtypes = [c_void_p]
	imageBuffer.restype = c_void_p
	buffer = imageBuffer(_sample_buffer)
	
	baseAddress = c.CVPixelBufferLockBaseAddress
	baseAddress.argtypes = [c_void_p, c_int]
	baseAddress.restype = None
	baseAddress(buffer, 0)
	
	ciContext = ObjCClass('CIContext')
	ctx = ciContext.contextWithOptions_(None)
	
	lockBaseAddress = c.CVPixelBufferLockBaseAddress
	lockBaseAddress.argtypes = [c_void_p, c_int]
	lockBaseAddress.restype = None
	lockBaseAddress(buffer, 0)
	
	cii = ObjCClass('CIImage').imageWithCVPixelBuffer_(ObjCInstance(buffer))
	
	cg = ctx.createCGImage_fromRect_(cii, cii.extent())
	
	conv2Png = c.UIImagePNGRepresentation 
	conv2Png.argtypes = [c_void_p]
	conv2Png.restype = ctypes.c_void_p
	uii = ObjCClass('UIImage').imageWithCGImage_(cg)
	data = ObjCInstance(conv2Png(uii.ptr))

	unlockBaseAddress = c.CVPixelBufferUnlockBaseAddress
	unlockBaseAddress.argtypes = [c_void_p, c_int]
	unlockBaseAddress.restype = None
	unlockBaseAddress(buffer, 0)
	
d = 'sampleBufferDelegate'
m = [captureOutput_didOutputSampleBuffer_fromConnection_]
p = ['AVCaptureVideoDataOutputSampleBufferDelegate']
sampleBufferDelegate = create_objc_class(d, methods=m, protocols=p)

class CameraImage(ui.View):
	global data
	def __init__(self, *args, **kwargs):
		device = 0
		self.session = ObjCClass('AVCaptureSession').alloc().init()
		self.session.setSessionPreset_('AVCaptureSessionPresetMedium')
		inputDevices = ObjCClass('AVCaptureDevice').devices()
		inputDevice = inputDevices[device]

		deviceInput = ObjCClass('AVCaptureDeviceInput').deviceInputWithDevice_error_(inputDevice, None)
		if self.session.canAddInput_(deviceInput):
			self.session.addInput_(deviceInput)
		self.output = ObjCClass('AVCaptureVideoDataOutput').alloc().init()
		
		self.session.addOutput_(self.output)
		self.delegate = sampleBufferDelegate.new()
		
		queue = c.dispatch_get_current_queue
		queue.restype = c_void_p
		q = ObjCInstance(queue())
		self.output.setSampleBufferDelegate_queue_(self.delegate, q)
		self.output.alwaysDiscardsLateVideoFrames = True
		self.name = 'Acid Simulator'
	
	def addScene(self):
		sv = SceneView()
		sv.scene = MyScene()
		sv.width = self.width
		sv.height = self.height
		self.add_subview(sv)
		
	def start(self):
		self.session.startRunning()
		
	def close(self):
		self.session.stopRunning()
		
class MyScene (Scene): 
	cnt = 0
	global data
	def setup(self):
		t_path = os.path.join(tempfile.gettempdir(), 't.png')
		self.filename = os.path.abspath(t_path)
		data.writeToFile_atomically_(self.filename, True)
		frame = ui.Image(self.filename).resizable_image(0,0,255,255)
		texture = Texture(frame)
		self.img = SpriteNode(texture, position=self.size/2,parent=self)
		self.img.shader = Shader(acid_shader)
		r_path = os.path.join(tempfile.gettempdir(), 'r')
		self.r=[sound.Recorder(r_path) for i in range(2)]
		self.r_active = self.r[0]
		self.r_active.record()
		
		self.wave = 5 -abs(max(self.r_active.meters['average']))/10
		self.img.shader.set_uniform('param', self.wave)
		self.img.effects_enabled = True
	def update(self): 
		data.writeToFile_atomically_(self.filename, True)
		frame = ui.Image(self.filename).resizable_image(0,0,255,255)
		texture = Texture(frame)
		self.img.texture = texture
		
		self.wave = 5 -abs(max(self.r_active.meters['average']))/10
		self.img.shader.set_uniform('param', self.wave)
		self.img.effects_enabled = True
		
cam = CameraImage()
cam.start()
cam.present('full_screen',orientations = ['landscape'])
cam.addScene()
cam.wait_modal()

cam.close()
