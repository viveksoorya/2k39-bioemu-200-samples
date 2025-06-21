from chimera.extension import EMO, manager

class Benchmark_EMO(EMO):
	def name(self):
		return 'Benchmark'
	def description(self):
		return 'Graphics benchmark utility.'
	def categories(self):
		return ['Utilities']
	def icon(self):
		return self.path('indy.png')
	def activate(self):
		self.module().show_benchmark_dialog()
		return None

manager.registerExtension(Benchmark_EMO(__file__))

def report_frame_rate():
	import Benchmark
	Benchmark.report_frame_rate()
	
from Accelerators import add_accelerator
add_accelerator('rt', 'Report frame rate each second', report_frame_rate)
