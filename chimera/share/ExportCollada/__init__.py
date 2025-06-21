_USE_THREAD = False	# TODO: figure out why this deadlocks

def write_collada(output):
	import chimera
	if _USE_THREAD:
		# x3dWrite doesn't give up the GIL, but, x3dOuput,
		# a Python file object, does.
		import os, threading
		(read, write) = os.pipe()
		x3dInput = os.fdopen(read, 'rb')
		x3dOutput = os.fdopen(write, 'wb')

		# consume piped X3D output in separate thread
		def consume(x3dInput=x3dInput, output=output):
			from . import x3d2collada
			import xml.etree.cElementTree as ET
			p = x3d2collada.ColladaProcessor("_initial_view_")
			ET.parse(x3dInput, parser=ET.XMLParser(target=p))
			p.write_file(output)
		consumer = threading.Thread(target=consume)
		consumer.start()
	else:
		import tempfile
		x3dOutput = tempfile.TemporaryFile()

	title = ""
	try:
		clipping = chimera.viewer.clipping
		chimera.viewer.clipping = True	# want hither/yon planes
		chimera.viewer.x3dWrite(x3dOutput, 0, title)
	finally:
		chimera.viewer.clipping = clipping
	if _USE_THREAD:
		# explicitly close so consumer can finish
		x3dOutput.close()
		consumer.join()
		x3dInput.close()
	else:
		x3dOutput.seek(0)
		from . import x3d2collada
		import xml.etree.cElementTree as ET
		p = x3d2collada.ColladaProcessor("_initial_view_")
		ET.parse(x3dOutput, parser=ET.XMLParser(target=p))
		x3dOutput.close()
		p.write_file(output)

	try:
		output.flush()
	except AttributeError:
		pass
