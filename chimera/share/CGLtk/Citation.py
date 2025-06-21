""" Citation:  show citation for literature reference"""

import Tkinter
from PIL import Image, ImageTk
import os

class Citation(Tkinter.Frame):
	"""Citation is treated as a Frame
		'cite' is the citation text
		'prefix'/'suffix' is text to precede/follow the citation
		'url' is the link to the publication data base.
		'pubmedID' is the PubMed ID, which can be supplied in lieu of 'url'
			if appropriate
		'image' is the path to the image file of publication data base logo icon.
		 the default is the PubMed icon.
	"""
	def __init__(self, master, cite, prefix=None, suffix=None,
			url=None, pubmedID=None, image='Default_PubMed'):
		Tkinter.Frame.__init__(self, master, bd=2, relief="raised")
		
		if prefix is not None:
			Tkinter.Label(self, text=prefix).grid(row=0, column=0)
		
		Tkinter.Label(self, justify="left", font=("Times", "12"),
			text=cite).grid(row=1, column=0)
		
		if url is None:
			if pubmedID:
				url = 'https://www.ncbi.nlm.nih.gov/pubmed/' + str(pubmedID)
		if url is not None:
			self.url = url
			self.PubIcon = Tkinter.Button(self, 
					bd=4,
					command=self._openURL,
					)
			if image == 'Default_PubMed':
				pkgdir = os.path.dirname(__file__)
				imagePath = os.path.join(pkgdir, "Default_PubMed.png")
			else:
				imagePath = image
			if os.path.exists(imagePath):
				iconImage = ImageTk.PhotoImage(Image.open(imagePath))
				self.PubIcon.config(image = iconImage)
				self.PubIcon.photo = iconImage
			else:
				self.PubIcon.config(text='PubMed')
			self.PubIcon.grid(row=1, column=1, sticky='se')
		if suffix is not None:
			Tkinter.Label(self, text=suffix).grid(row=2, column=0)
	
	def _openURL(self):
		from chimera.help import display
		display(self.url)
		return
