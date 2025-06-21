class EMDB_WS:
	WSDL_URL = "http://emsearch.rutgers.edu/EMSearchWS/services/EMBusinessService?wsdl"
	RESPONSE_URL = "http://emdb.rutgers.edu/ws/response.xsd"

	def __init__(self):
		# Create WSDL client
		from suds.client import Client
		self.sudsClient = Client(self.WSDL_URL)
		self.emdbws = self.sudsClient.service
		#print self.sudsClient
		# Create parser for returned XML
		from suds.reader import DocumentReader
		reader = DocumentReader(self.sudsClient.options)
		doc = reader.open(self.RESPONSE_URL)
		from suds.xsd.schema import Schema
		schema = Schema(doc.root(), "", self.sudsClient.options)
		self.resultsetType = schema.elements[("resultset", None)]
		from suds.umx.typed import Typed
		self.umxTyped = Typed(schema)

	def _getResults(self, xml):
		from suds.sax.parser import Parser
		resultRoot = Parser().parse(string=xml).root()
		results = self.umxTyped.process(resultRoot, self.resultsetType)
		return results

	def rowValues(self, results):
		rv = []
		try:
			rows = results.row
		except AttributeError:
			# Must be an empty answer
			pass
		else:
			for row in rows:
				values = dict([ (a, getattr(row, a))
						for a in dir(row)
						if not a.startswith('_') ])
				rv.append(values)
		return rv

	def dumpResults(self, results):
		for row in results.row:
			self._dumpRow(row)

	def _dumpRow(self, row):
		print "instance of", row.__class__
		for attr in self.ResultAttrList:
			try:
				value = getattr(row, attr)
				if value is not None:
					print "  %s: %s" % (attr, value)
			except AttributeError:
				pass

	def getResultSetXMLByAuthor(self, author):
		resp = self.emdbws.getResultSetXMLByAuthor(author)
		return self._getResults(resp)

	def getResultSetXMLByID(self, accession):
		resp = self.emdbws.getResultSetXMLByID(accession)
		return self._getResults(resp)

	def getResultSetXMLByTitle(self, title):
		resp = self.sudsClient.service.getResultSetXMLByTitle(title)
		return self._getResults(resp)

	def getSampleNameXML(self, id):
		resp = self.emdbws.getSampleNameXML(id)
		return self._getResults(resp)

	def findContourLevelByAccessionCode(self, accession):
		resp = self.emdbws.findContourLevelByAccessionCode(accession)
		return self._getResults(resp)

	def findFittedPDBidsByAccessionCode(self, accession):
		resp = self.emdbws.findFittedPDBidsByAccessionCode(accession)
		return self._getResults(resp)

	def searchSampleNameByID(self, id):
		resp = self.emdbws.searchSampleNameByID(id)
		return self._getResults(resp)

if __name__ == "__main__":
	ws = EMDB_WS()
	accession = "1249"
	author = "taylor"
	title = "hiv"
	print "findContourLevelByAccessionCode", accession
	ws.dumpResults(ws.findContourLevelByAccessionCode(accession))
	print
	print "findFittedPDBidsByAccessionCode", accession
	ws.dumpResults(ws.findFittedPDBidsByAccessionCode(accession))
	print
	print "getResultSetXMLByID", accession
	ws.dumpResults(ws.getResultSetXMLByID(accession))
	print
	print "getResultSetXMLByAuthor", accession
	ws.dumpResults(ws.getResultSetXMLByAuthor(author))
	print
	print "getResultSetXMLByTitle", accession
	ws.dumpResults(ws.getResultSetXMLByTitle(title))
